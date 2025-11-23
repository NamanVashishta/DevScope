import glob
import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import google.generativeai as genai

from db import AtlasClient
from monitor import VisualMonitor

logger = logging.getLogger(__name__)


class BatchSummarizer:
    """
    Periodically uploads session screenshots, asks Gemini for a standup summary,
    persists it to Mongo, and cleans up local/remote storage.
    """

    SYSTEM_PROMPT_TEMPLATE = """
You are a Senior Technical Lead writing a formal Daily Standup Report. The User's Stated Goal was: "{session_goal}".

INTELLIGENT NOISE FILTER:

Social Media/Video (Reddit, YouTube, X): Do NOT blindly ignore them. Analyze the content.

KEEP IT if it is Technical/Educational (e.g., "Watching a Python Tutorial", "Reading a StackOverflow thread on Reddit", "Viewing a Conference Talk"). Label this as "Research".

IGNORE IT only if it is clearly Entertainment (e.g., Music Videos, Memes, Gaming, Politics). Do not mention these in the report.

OUTPUT FORMAT (Markdown): Write a concise summary of the session:

Features Implemented: (What code was actually written/changed?)

Bugs Debugged: (What specific errors were encountered and fixed?)

Key Research: (What documentation, tutorials, or technical discussions were reviewed?)

Context Score: (0-10, how focused was this session based on the filtered evidence?)
"""

    def __init__(
        self,
        monitor: VisualMonitor,
        *,
        hivemind_client: Optional[AtlasClient] = None,
        interval_seconds: int = 1800,
    ) -> None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError("Set GEMINI_API_KEY before using the batch summarizer.")
        genai.configure(api_key=api_key)

        self.monitor = monitor
        self.interval_seconds = max(interval_seconds, 60)
        self.hivemind = hivemind_client or AtlasClient(collection_name="session_summaries")
        self._model_name = "gemini-1.5-pro"

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------ Public API
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            logger.warning("BatchSummarizer already running.")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="BatchSummarizer", daemon=True)
        self._thread.start()
        logger.info("BatchSummarizer started with %ss interval.", self.interval_seconds)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=self.interval_seconds + 5)
        logger.info("BatchSummarizer stopped.")

    def summarize_active_session(self) -> Optional[str]:
        """Manual trigger hook (e.g., after a git commit)."""
        return self._summarize_session()

    # ----------------------------------------------------------------- Internals
    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._summarize_session()
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.exception("Batch summarization failed: %s", exc)
            finally:
                self._stop_event.wait(self.interval_seconds)

    def _summarize_session(self, session_id: Optional[str] = None) -> Optional[str]:
        session = self._resolve_session(session_id)
        if not session:
            logger.debug("No active session available for batch summarization.")
            return None

        frame_paths = self._list_session_frames(session.temp_dir)
        if not frame_paths:
            logger.debug("No frames found for session %s; skipping batch summary.", session.id)
            return None

        uploaded_files: List[Tuple[object, str]] = []
        try:
            uploaded_files = self._upload_frames(frame_paths)
            if not uploaded_files:
                logger.warning("All uploads failed for session %s.", session.id)
                return None

            summary_text = self._generate_summary(session.goal, [f for f, _ in uploaded_files])
            if not summary_text:
                logger.warning("Gemini returned empty summary for session %s.", session.id)
                return None

            minutes = self._calculate_time_window_minutes(frame_paths)
            identity = self._identity_snapshot()
            self._persist_summary(identity, session.id, summary_text, minutes)
            logger.info("Batch summary stored for session %s.", session.id)
            return summary_text
        finally:
            self._cleanup_remote(uploaded_files)
            self._cleanup_local(frame_paths)

    def _resolve_session(self, session_id: Optional[str]):
        sid = session_id or self.monitor.get_active_session_id()
        if not sid:
            return None
        return self.monitor.get_session(sid)

    @staticmethod
    def _list_session_frames(temp_dir: str) -> List[str]:
        return sorted(glob.glob(os.path.join(temp_dir, "*.png")))

    def _upload_frames(self, paths: Sequence[str]) -> List[Tuple[object, str]]:
        uploaded = []
        for path in paths:
            try:
                logger.debug("Uploading frame %s", path)
                remote = genai.upload_file(path)
                remote = self._wait_for_active(remote)
                if not remote:
                    logger.warning("Upload stalled or failed for %s; skipping.", path)
                    continue
                uploaded.append((remote, path))
            except Exception as exc:
                logger.warning("Failed to upload %s: %s", path, exc)
        return uploaded

    @staticmethod
    def _wait_for_active(remote_file, timeout: int = 90, poll_interval: float = 1.5):
        start = time.time()
        current = remote_file
        while current:
            state = getattr(getattr(current, "state", None), "name", "")
            if state == "ACTIVE":
                return current
            if state and state not in {"PENDING", "PROCESSING"}:
                logger.warning("File %s entered state %s", getattr(current, "name", "?"), state)
                return None
            if time.time() - start > timeout:
                logger.warning("Timed out waiting for file %s to activate.", getattr(current, "name", "?"))
                return None
            time.sleep(poll_interval)
            current = genai.get_file(current.name)
        return None

    def _generate_summary(self, session_goal: str, remote_files: Sequence[object]) -> str:
        if not remote_files:
            return ""
        system_prompt = self.SYSTEM_PROMPT_TEMPLATE.format(session_goal=session_goal or "Unknown")
        model = genai.GenerativeModel(self._model_name, system_instruction=system_prompt)
        parts = list(remote_files)
        parts.append({"text": "Analyze the attached visual timeline and write the standup report now."})
        response = model.generate_content(parts)
        return (getattr(response, "text", "") or "").strip()

    def _identity_snapshot(self) -> dict:
        snapshot_fn = getattr(self.monitor, "_identity_snapshot", None)
        if callable(snapshot_fn):
            return snapshot_fn()
        return {
            "user_id": os.environ.get("HIVEMIND_USER_ID"),
            "org_id": os.environ.get("HIVEMIND_ORG_ID"),
        }

    def _persist_summary(
        self,
        identity: dict,
        session_id: str,
        summary_text: str,
        minutes: int,
    ) -> None:
        if not self.hivemind or not summary_text:
            return
        document = {
            "org_id": identity.get("org_id"),
            "user_id": identity.get("user_id"),
            "session_id": session_id,
            "timestamp": datetime.utcnow(),
            "summary_text": summary_text,
            "time_range_minutes": minutes,
        }
        if not document.get("org_id") or not document.get("user_id"):
            logger.warning("Missing identity metadata; summary not stored.")
            return
        if not self.hivemind.save_summary(document):
            logger.warning("Failed to persist batch summary for session %s.", session_id)

    @staticmethod
    def _calculate_time_window_minutes(paths: Sequence[str]) -> int:
        if not paths:
            return 0
        mtimes = [os.path.getmtime(path) for path in paths]
        span_seconds = max(mtimes) - min(mtimes) if len(mtimes) > 1 else 0
        return max(1, int(span_seconds // 60) or 1)

    @staticmethod
    def _cleanup_remote(uploaded: Sequence[Tuple[object, str]]) -> None:
        for remote, _ in uploaded:
            try:
                genai.delete_file(remote.name)
            except Exception as exc:
                logger.debug("Failed to delete remote file %s: %s", getattr(remote, "name", "?"), exc)

    @staticmethod
    def _cleanup_local(paths: Sequence[str]) -> None:
        for path in paths:
            try:
                os.remove(path)
            except FileNotFoundError:
                continue
            except OSError as exc:
                logger.debug("Failed to delete local frame %s: %s", path, exc)


__all__ = ["BatchSummarizer"]


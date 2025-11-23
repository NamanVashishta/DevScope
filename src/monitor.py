import json
import logging
import os
import platform
import re
import shutil
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Deque, Dict, List, Optional, Tuple

import mss
from PIL import Image
from activity_schema import ActivityRecord
from constants import DEFAULT_ORG_ID
from api_models import create_model

from db import HiveMindClient
from prompts import SMART_EXTRACTOR_PROMPT
from session import Session

try:
    from AppKit import NSWorkspace  # type: ignore
    from Quartz import (  # type: ignore
        CGWindowListCopyWindowInfo,
        kCGWindowListOptionOnScreenOnly,
        kCGNullWindowID,
    )
except ImportError:  # pragma: no cover - optional on non-mac systems
    NSWorkspace = None
    CGWindowListCopyWindowInfo = None
    kCGWindowListOptionOnScreenOnly = None
    kCGNullWindowID = None

logger = logging.getLogger(__name__)


@dataclass
class ActiveWindowSnapshot:
    """Represents the current active window, including geometry if available."""

    app: str = "Unknown"
    title: str = "Unknown"
    bounds: Optional[Tuple[int, int, int, int]] = None


class ActiveWindowInspector:
    """Caches frontmost window metadata to avoid redundant OS calls."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cache = ActiveWindowSnapshot()
        self._last_fetch = 0.0

    def snapshot(self, *, cache_max_age: float = 0.25) -> ActiveWindowSnapshot:
        now = time.time()
        with self._lock:
            if cache_max_age >= 0 and now - self._last_fetch <= cache_max_age:
                return self._cache
            self._cache = self._fetch_snapshot()
            self._last_fetch = now
            return self._cache

    def _fetch_snapshot(self) -> ActiveWindowSnapshot:
        if platform.system() != "Darwin" or not NSWorkspace or not CGWindowListCopyWindowInfo:
            return ActiveWindowSnapshot()

        try:
            workspace = NSWorkspace.sharedWorkspace()
            active_app = workspace.frontmostApplication()
            app_name = active_app.localizedName() if active_app else "Unknown"
            pid = active_app.processIdentifier() if active_app else None

            window_title = "Unknown"
            bounds: Optional[Tuple[int, int, int, int]] = None
            if pid:
                windows = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
                window_title, bounds = self._extract_window_details(pid, windows)
            return ActiveWindowSnapshot(app=app_name, title=window_title, bounds=bounds)
        except Exception:
            return ActiveWindowSnapshot()

    @staticmethod
    def _extract_window_details(pid: int, windows: List[dict]) -> Tuple[str, Optional[Tuple[int, int, int, int]]]:
        for window in windows or []:
            if window.get("kCGWindowOwnerPID") != pid:
                continue
            if window.get("kCGWindowLayer", 0) != 0:
                continue
            name = window.get("kCGWindowName") or "Unknown"
            bounds_dict = window.get("kCGWindowBounds") or {}
            width = int(bounds_dict.get("Width", 0))
            height = int(bounds_dict.get("Height", 0))
            if width <= 0 or height <= 0:
                continue
            bounds = (
                int(bounds_dict.get("X", 0)),
                int(bounds_dict.get("Y", 0)),
                width,
                height,
            )
            return name, bounds
        return "Unknown", None


ACTIVE_WINDOW_INSPECTOR = ActiveWindowInspector()


class VisualMonitor:
    """Captures screenshots, labels them with Gemini, stores metadata per session."""

    SYSTEM_PROMPT_TEMPLATE = SMART_EXTRACTOR_PROMPT

    def __init__(
        self,
        capture_interval: int = 10,
        max_entries: int = 180,
        temp_root: Optional[str] = None,
        model_name: str = "gemini-2.0-flash",
        privacy_filter: Optional[Callable[[], bool]] = None,
        on_entry: Optional[Callable[[ActivityRecord], None]] = None,
        hivemind_client: Optional[HiveMindClient] = None,
    ):
        self.capture_interval = capture_interval
        self.max_entries = max_entries
        self.temp_root = temp_root or os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp_disk")
        os.makedirs(self.temp_root, exist_ok=True)
        self.model = create_model(model_name)
        self.privacy_filter = privacy_filter or default_privacy_filter()
        self.on_entry = on_entry
        self.hivemind = hivemind_client
        self.identity: Dict[str, Optional[str]] = {
            "user_id": os.environ.get("HIVEMIND_USER_ID"),
            "display_name": os.environ.get("HIVEMIND_USER_NAME"),
        }

        self.sessions: Dict[str, Session] = {}
        self.active_session_id: Optional[str] = None

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    # Session management ---------------------------------------------------

    def create_session(self, project_name: str, repo_path: str, goal: str) -> Session:
        session_id = uuid.uuid4().hex
        project_slug = _slugify(project_name)
        temp_dir = os.path.join(self.temp_root, project_slug)
        os.makedirs(temp_dir, exist_ok=True)
        session = Session(
            id=session_id,
            project_name=project_name,
            project_slug=project_slug,
            goal=goal,
            repo_path=repo_path,
            temp_dir=temp_dir,
            ring_buffer=deque(maxlen=self.max_entries),
        )
        with self._lock:
            self.sessions[session_id] = session
            if not self.active_session_id:
                self.active_session_id = session_id
        logger.info("Created session %s for project %s", session_id, project_name)
        return session

    def delete_session(self, session_id: str) -> None:
        session = None
        with self._lock:
            session = self.sessions.pop(session_id, None)
            if session and self.active_session_id == session_id:
                self.active_session_id = next(iter(self.sessions), None)
        if session:
            shutil.rmtree(os.path.join(self.temp_root, session.project_slug), ignore_errors=True)
            logger.info("Deleted session %s", session_id)

    def switch_session(self, session_id: str) -> None:
        with self._lock:
            if session_id not in self.sessions:
                raise ValueError(f"Session {session_id} not found.")
            self.active_session_id = session_id
        logger.info("Switched to session %s", session_id)

    def get_sessions_metadata(self) -> List[dict]:
        with self._lock:
            return [
                {
                    "id": session.id,
                    "project_name": session.project_name,
                    "project_slug": session.project_slug,
                    "goal": session.goal,
                    "repo_path": session.repo_path,
                }
                for session in self.sessions.values()
            ]

    def get_session(self, session_id: str) -> Optional[Session]:
        with self._lock:
            return self.sessions.get(session_id)

    def get_active_session_id(self) -> Optional[str]:
        with self._lock:
            return self.active_session_id

    def snapshot(self, session_id: Optional[str] = None) -> List[ActivityRecord]:
        with self._lock:
            sid = session_id or self.active_session_id
            session = self.sessions.get(sid) if sid else None
            if not session:
                return []
            return list(session.ring_buffer)

    def get_active_buffer(
        self,
        *,
        session_id: Optional[str] = None,
        window_minutes: int = 30,
    ) -> List[ActivityRecord]:
        """
        Return buffer entries for the target session limited to the recent window.

        Used by Git triggers to produce commit context without dumping the entire deque.
        """
        cutoff = datetime.utcnow() - timedelta(minutes=max(window_minutes, 1))
        with self._lock:
            sid = session_id or self.active_session_id
            session = self.sessions.get(sid) if sid else None
            if not session:
                return []
            return [
                entry
                for entry in session.ring_buffer
                if entry.timestamp >= cutoff and entry.privacy_state == "allowed"
            ]

    def update_identity(
        self,
        *,
        user_id: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> None:
        """Refresh the identity tags used for Hive Mind uploads."""
        with self._lock:
            if user_id is not None:
                self.identity["user_id"] = user_id or None
            if display_name is not None:
                self.identity["display_name"] = display_name or None

    # Thread control -------------------------------------------------------

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            logger.warning("VisualMonitor already running.")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="DevScopeMonitor", daemon=True)
        self._thread.start()
        logger.info("VisualMonitor started.")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=self.capture_interval + 2)
        logger.info("VisualMonitor stopped.")

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    # Internal helpers ----------------------------------------------------

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                session = self._get_active_session()
                if not session:
                    time.sleep(1)
                    continue

                if self.privacy_filter and not self.privacy_filter():
                    logger.debug("Privacy filter blocked capture.")
                    time.sleep(self.capture_interval)
                    continue

                snapshot = get_active_window_snapshot(cache_max_age=0.0)
                image_path = self._capture_frame(session.temp_dir)
                if not image_path:
                    time.sleep(self.capture_interval)
                    continue

                system_prompt = self.SYSTEM_PROMPT_TEMPLATE.format(
                    user_goal=session.goal,
                    active_app=snapshot.app,
                    window_title=snapshot.title,
                    focus_bounds=_format_focus_bounds(snapshot.bounds),
                )

                metadata = self._label_frame(image_path, system_prompt)
                identity = self._identity_snapshot()
                record = self._build_activity_record(
                    session=session,
                    snapshot=snapshot,
                    metadata=metadata,
                    image_path=image_path,
                    identity=identity,
                )

                if record.privacy_state != "allowed":
                    self._delete_file(image_path)
                    record.screenshot_path = None
                    logger.info(
                        "[%s] Dropped screenshot due to privacy_state=%s deep_state=%s",
                        session.project_name,
                        record.privacy_state,
                        record.deep_work_state,
                    )

                self._append_entry(session, record)
                self._sync_hivemind(session, record)
                if self.on_entry:
                    self.on_entry(record)
            except Exception as exc:
                logger.exception("Monitor loop error: %s", exc)
            finally:
                time.sleep(self.capture_interval)

    def _build_activity_record(
        self,
        *,
        session: Session,
        snapshot: ActiveWindowSnapshot,
        metadata: Dict,
        image_path: str,
        identity: Dict[str, Optional[str]],
    ) -> ActivityRecord:
        metadata = metadata or {}
        task_label = self._clean_string(
            metadata.get("task") or metadata.get("activity_summary") or metadata.get("activity_type"),
            fallback="Unknown Task",
        )
        activity_type = self._clean_string(
            metadata.get("activity_type") or metadata.get("activity_kind"),
            fallback="UNKNOWN",
        ).upper()
        technical_context = self._clean_string(metadata.get("technical_context"), fallback="N/A")
        app_name = self._clean_string(
            metadata.get("app_name") or metadata.get("app"),
            fallback=snapshot.app or "Unknown",
        )
        alignment_score = self._safe_int(metadata.get("alignment_score"))
        is_deep_work = bool(metadata.get("is_deep_work"))
        deep_state = (metadata.get("deep_work_state") or ("deep_work" if is_deep_work else "distracted")).lower()
        privacy_state = (metadata.get("privacy_state") or ("allowed" if deep_state == "deep_work" else "blocked")).lower()

        record = ActivityRecord(
            timestamp=datetime.utcnow(),
            session_id=session.id,
            project_name=session.project_name,
            project_slug=session.project_slug,
            session_goal=session.goal,
            repo_path=session.repo_path,
            task=task_label,
            activity_type=activity_type,
            technical_context=technical_context,
            app_name=app_name,
            active_app=snapshot.app,
            window_title=snapshot.title,
            alignment_score=alignment_score,
            is_deep_work=is_deep_work,
            deep_work_state=deep_state,
            privacy_state=privacy_state,
            focus_bounds=snapshot.bounds,
            error_code=self._pick_error_code(metadata, technical_context),
            function_target=self._clean_string(metadata.get("function_target") or metadata.get("function_name")),
            documentation_title=self._clean_string(metadata.get("documentation_title") or metadata.get("doc_title")),
            doc_url=self._clean_string(metadata.get("documentation_url") or metadata.get("doc_url")),
            screenshot_path=image_path,
            user_id=identity.get("user_id"),
            user_display=identity.get("display_name") or identity.get("user_id"),
            org_id=DEFAULT_ORG_ID,
        )
        return record

    def _capture_frame(self, temp_dir: str) -> Optional[str]:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        file_path = os.path.join(temp_dir, f"frame_{timestamp}.png")

        with mss.mss() as sct:
            monitor = sct.monitors[0]  # full virtual screen
            raw = sct.grab(monitor)
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
            img.thumbnail((1920, 1080), Image.LANCZOS)
            img.save(file_path)
            logger.debug("Captured frame %s", file_path)
            return file_path

    def _label_frame(self, image_path: str, system_prompt: str) -> dict:
        prompt = (
            "Describe the active engineering task, IDE/app name, and any visible clues "
            "like error codes or file names. Output valid JSON only."
        )
        response = self.model.call_model(user_prompt=prompt, system_prompt=system_prompt, image_paths=[image_path])
        return self._safe_parse_metadata(response)

    def _safe_parse_metadata(self, text: str) -> dict:
        fallback = {
            "task": "Unknown Task",
            "activity_type": "UNKNOWN",
            "technical_context": "Unparsed response",
            "app_name": "Unknown",
            "alignment_score": None,
            "is_deep_work": False,
            "deep_work_state": "distracted",
            "privacy_state": "blocked",
            "error_code": None,
            "function_target": None,
            "documentation_title": None,
            "documentation_url": None,
        }
        try:
            cleaned = text.strip()
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start == -1 or end == -1:
                raise ValueError("JSON braces not found.")
            parsed = json.loads(cleaned[start : end + 1])
        except Exception as exc:
            logger.warning("Failed to parse Gemini response '%s': %s", text, exc)
            parsed = {}
        return self._normalize_metadata({**fallback, **parsed})

    @staticmethod
    def _normalize_metadata(metadata: Dict) -> Dict:
        metadata["activity_type"] = str(metadata.get("activity_type") or metadata.get("task") or "UNKNOWN").upper()
        metadata["task"] = metadata.get("task") or metadata["activity_type"].title()
        metadata["app_name"] = metadata.get("app_name") or metadata.get("app") or "Unknown"
        metadata["technical_context"] = metadata.get("technical_context") or "Unspecified context"
        metadata["deep_work_state"] = (
            metadata.get("deep_work_state")
            or ("deep_work" if metadata.get("is_deep_work") else "distracted")
        )
        metadata["privacy_state"] = (
            metadata.get("privacy_state")
            or ("allowed" if metadata["deep_work_state"] == "deep_work" else "blocked")
        )
        return metadata

    def _append_entry(self, session: Session, entry: ActivityRecord) -> None:
        with self._lock:
            if len(session.ring_buffer) == session.ring_buffer.maxlen:
                oldest = session.ring_buffer.popleft()
                if oldest.screenshot_path:
                    self._delete_file(oldest.screenshot_path)
            session.ring_buffer.append(entry)
        logger.info(
            "[%s] Buffered frame - task=%s app=%s deep_work=%s",
            session.project_name,
            entry.task,
            entry.app_name,
            entry.is_deep_work,
        )

    def _sync_hivemind(self, session: Session, entry: ActivityRecord) -> None:
        if entry.privacy_state != "allowed" or not entry.is_deep_work:
            logger.debug("Skipping Hive Mind sync due to privacy_state=%s", entry.privacy_state)
            return

        identity = self._identity_snapshot()
        entry.user_id = entry.user_id or identity.get("user_id")
        entry.user_display = entry.user_display or identity.get("display_name") or entry.user_id
        entry.org_id = DEFAULT_ORG_ID
        entry.project_name = session.project_name

        if (
            not self.hivemind
            or not self.hivemind.enabled
            or not entry.user_id
        ):
            return

        payload = entry.to_payload()
        payload.setdefault("summary", f"{entry.task} | {entry.technical_context}")
        payload.setdefault("session_goal", entry.session_goal or session.goal)
        payload.setdefault("repo_path", entry.repo_path or session.repo_path)

        if not self.hivemind.publish_activity(payload):
            logger.debug("Hive Mind sync skipped or failed for session %s", session.id)

    def _identity_snapshot(self) -> Dict[str, Optional[str]]:
        with self._lock:
            snapshot = dict(self.identity)
        snapshot.setdefault("org_id", DEFAULT_ORG_ID)
        return snapshot

    def _delete_file(self, path: str) -> None:
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError as exc:
            logger.debug("Failed to delete %s: %s", path, exc)

    def _get_active_session(self) -> Optional[Session]:
        with self._lock:
            if not self.active_session_id:
                return None
            return self.sessions.get(self.active_session_id)

    @staticmethod
    def _safe_int(value) -> Optional[int]:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _clean_string(value, fallback: str = "") -> str:
        if value is None:
            return fallback
        text = str(value).strip()
        return text or fallback

    @staticmethod
    def _pick_error_code(metadata: Dict, technical_context: str) -> Optional[str]:
        code = metadata.get("error_code")
        if isinstance(code, str) and code.strip():
            return code.strip()
        if isinstance(code, int):
            return str(code)
        if technical_context:
            match = re.search(r"\b([45]\d{2})\b", technical_context)
            if match:
                return match.group(1)
        return None


def default_privacy_filter() -> Callable[[], bool]:
    blocklist_raw = os.environ.get("DEVSCOPE_PRIVACY_APPS", "")
    blocked = {item.strip().lower() for item in blocklist_raw.split(",") if item.strip()}
    if not blocked or platform.system() != "Darwin":
        return lambda: True

    def _mac_privacy_guard() -> bool:
        snapshot = get_active_window_snapshot(cache_max_age=0.0)
        name = snapshot.app or ""
        return name.lower() not in blocked

    return _mac_privacy_guard


def get_active_window_snapshot(cache_max_age: float = 0.25) -> ActiveWindowSnapshot:
    """Return cached metadata for the currently focused window."""
    return ACTIVE_WINDOW_INSPECTOR.snapshot(cache_max_age=cache_max_age)


def get_active_window_metadata() -> Tuple[str, str]:
    """Backwards-compatible helper returning app + title."""
    snapshot = get_active_window_snapshot()
    return snapshot.app, snapshot.title


def _format_focus_bounds(bounds: Optional[Tuple[int, int, int, int]]) -> str:
    if not bounds:
        return "Unknown"
    x, y, width, height = bounds
    return f"x={x}, y={y}, width={width}, height={height}"


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned or "project"


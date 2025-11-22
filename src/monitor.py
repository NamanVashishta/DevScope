import json
import logging
import os
import platform
import shutil
import threading
import time
import uuid
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Deque, Dict, List, Optional, Tuple

import mss
from PIL import Image
from api_models import create_model
from hivemind import HiveMindClient
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
class VisualEntry:
    timestamp: datetime
    task: str
    app: str
    technical_context: str
    is_deep_work: bool
    image_path: str
    session_id: str
    active_app: str = ""
    window_title: str = ""
    alignment_score: Optional[int] = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


class VisualMonitor:
    """Captures screenshots, labels them with Gemini, stores metadata per session."""

    SYSTEM_PROMPT_TEMPLATE = """You are a Senior Technical Project Manager monitoring a developer's workflow.

USER STATED GOAL: "{user_goal}"

The user is actively typing in: "{active_app}" (window: "{window_title}").
The attached screenshot is a panoramic capture of every monitor, so background apps may appear (Spotify, Discord, etc.).
Use those peripheral clues for context, but judge 'Deep Work' primarily by the active application and its alignment with the goal.

Analyze the attached screenshot of their desktop.
Your job is to determine if they are on track and extract technical context.

Output a RAW JSON object with this exact schema:
{{
    "app_name": "string (e.g., VS Code, Chrome, Terminal)",
    "activity_type": "one of [CODING, DEBUGGING, RESEARCHING, COMMUNICATING, IDLE, DISTRACTED]",
    "technical_context": "string (Extract specific error codes, library names, or function names visible. Max 15 words.)",
    "alignment_score": "integer 0-100 (How much does this screen align with the goal: '{user_goal}'?)",
    "is_deep_work": boolean (True if activity aligns with the goal. False if social media/unrelated browsing.)
}}

GUIDELINES:
1. **Context Extraction:** If you see a StackOverflow page, extract the error being researched. If you see a Terminal, extract the last command.
2. **Distraction Logic:** - If the App is Social Media/YouTube AND the content is unrelated to '{user_goal}', is_deep_work is FALSE.
   - If the App is VS Code/Terminal, is_deep_work is usually TRUE.

RETURN ONLY JSON. NO MARKDOWN."""

    def __init__(
        self,
        capture_interval: int = 10,
        max_entries: int = 180,
        temp_root: Optional[str] = None,
        model_name: str = "gemini-2.0-flash",
        privacy_filter: Optional[Callable[[], bool]] = None,
        on_entry: Optional[Callable[[VisualEntry], None]] = None,
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
        self.hivemind_user_id = os.environ.get("HIVEMIND_USER_ID")
        self.hivemind_user_name = os.environ.get("HIVEMIND_USER_NAME", self.hivemind_user_id or "")
        self.hivemind_org_id = os.environ.get("HIVEMIND_ORG_ID")

        self.sessions: Dict[str, Session] = {}
        self.active_session_id: Optional[str] = None

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    # Session management ---------------------------------------------------

    def create_session(self, name: str, repo_path: str, goal: str) -> Session:
        session_id = uuid.uuid4().hex
        temp_dir = os.path.join(self.temp_root, session_id)
        os.makedirs(temp_dir, exist_ok=True)
        session = Session(
            id=session_id,
            name=name,
            goal=goal,
            repo_path=repo_path,
            temp_dir=temp_dir,
            ring_buffer=deque(maxlen=self.max_entries),
        )
        with self._lock:
            self.sessions[session_id] = session
            if not self.active_session_id:
                self.active_session_id = session_id
        logger.info("Created session %s (%s)", session_id, name)
        return session

    def delete_session(self, session_id: str) -> None:
        session = None
        with self._lock:
            session = self.sessions.pop(session_id, None)
            if session and self.active_session_id == session_id:
                self.active_session_id = next(iter(self.sessions), None)
        if session:
            shutil.rmtree(session.temp_dir, ignore_errors=True)
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
                    "name": session.name,
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

    def snapshot(self, session_id: Optional[str] = None) -> List[VisualEntry]:
        with self._lock:
            sid = session_id or self.active_session_id
            session = self.sessions.get(sid) if sid else None
            if not session:
                return []
            return list(session.ring_buffer)

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

                image_path = self._capture_frame(session.temp_dir)
                if not image_path:
                    time.sleep(self.capture_interval)
                    continue

                active_app, window_title = get_active_window_metadata()
                system_prompt = self.SYSTEM_PROMPT_TEMPLATE.format(
                    user_goal=session.goal,
                    active_app=active_app,
                    window_title=window_title,
                )

                metadata = self._label_frame(image_path, system_prompt)
                entry = VisualEntry(
                    timestamp=datetime.utcnow(),
                    task=metadata.get("activity_type") or metadata.get("task", "Unknown"),
                    app=metadata.get("app_name") or metadata.get("app", "Unknown"),
                    technical_context=metadata.get("technical_context", "N/A"),
                    is_deep_work=bool(metadata.get("is_deep_work", False)),
                    image_path=image_path,
                    session_id=session.id,
                    active_app=active_app,
                    window_title=window_title,
                    alignment_score=self._safe_int(metadata.get("alignment_score")),
                )
                self._append_entry(session, entry)
                self._sync_hivemind(session, entry)
                if self.on_entry:
                    self.on_entry(entry)
            except Exception as exc:
                logger.exception("Monitor loop error: %s", exc)
            finally:
                time.sleep(self.capture_interval)

    def _capture_frame(self, temp_dir: str) -> Optional[str]:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        file_path = os.path.join(temp_dir, f"frame_{timestamp}.png")

        with mss.mss() as sct:
            monitor = sct.monitors[0]  # full virtual screen
            raw = sct.grab(monitor)
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
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
        try:
            cleaned = text.strip()
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start == -1 or end == -1:
                raise ValueError("JSON braces not found.")
            return json.loads(cleaned[start : end + 1])
        except Exception as exc:
            logger.warning("Failed to parse Gemini response '%s': %s", text, exc)
            return {
                "task": "Unknown",
                "app": "Unknown",
                "technical_context": "Unparsed response",
                "is_deep_work": False,
            }

    def _append_entry(self, session: Session, entry: VisualEntry) -> None:
        with self._lock:
            if len(session.ring_buffer) == session.ring_buffer.maxlen:
                oldest = session.ring_buffer.popleft()
                self._delete_file(oldest.image_path)
            session.ring_buffer.append(entry)
        logger.info(
            "[%s] Buffered frame - task=%s app=%s deep_work=%s",
            session.name,
            entry.task,
            entry.app,
            entry.is_deep_work,
        )

    def _sync_hivemind(self, session: Session, entry: VisualEntry) -> None:
        if (
            not entry.is_deep_work
            or not self.hivemind
            or not self.hivemind.enabled
            or not self.hivemind_org_id
            or not self.hivemind_user_id
        ):
            return

        payload = {
            "timestamp": entry.timestamp,
            "session_id": session.id,
            "project_name": session.name or session.goal,
            "session_goal": session.goal,
            "repo_path": session.repo_path,
            "user_id": self.hivemind_user_id,
            "user_display": self.hivemind_user_name or self.hivemind_user_id,
            "org_id": self.hivemind_org_id,
            "summary": f"{entry.task} | {entry.technical_context}",
            "task": entry.task,
            "technical_context": entry.technical_context,
            "app_name": entry.app,
            "active_app": entry.active_app,
            "window_title": entry.window_title,
            "alignment_score": entry.alignment_score,
            "is_deep_work": entry.is_deep_work,
            "source": "devscope-vision",
        }

        if not self.hivemind.publish_activity(payload):
            logger.debug("Hive Mind sync skipped or failed for session %s", session.id)

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


def default_privacy_filter() -> Callable[[], bool]:
    blocklist_raw = os.environ.get("DEVSCOPE_PRIVACY_APPS", "")
    blocked = {item.strip().lower() for item in blocklist_raw.split(",") if item.strip()}
    if not blocked or platform.system() != "Darwin":
        return lambda: True

    def _mac_privacy_guard() -> bool:
        try:
            from AppKit import NSWorkspace  # type: ignore

            app = NSWorkspace.sharedWorkspace().frontmostApplication()
            name = app.localizedName() if app else ""
            return name.lower() not in blocked
        except Exception:
            return True

    return _mac_privacy_guard


def get_active_window_metadata() -> Tuple[str, str]:
    if platform.system() != "Darwin" or not NSWorkspace or not CGWindowListCopyWindowInfo:
        return "Unknown", "Unknown"
    try:
        workspace = NSWorkspace.sharedWorkspace()
        active_app = workspace.frontmostApplication()
        app_name = active_app.localizedName() if active_app else "Unknown"
        pid = active_app.processIdentifier() if active_app else None

        window_title = "Unknown"
        if pid:
            windows = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
            for window in windows:
                if window.get("kCGWindowOwnerPID") == pid:
                    name = window.get("kCGWindowName")
                    if name:
                        window_title = name
                        break
        return app_name, window_title
    except Exception:
        return "Unknown", "Unknown"


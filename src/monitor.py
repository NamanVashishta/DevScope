import json
import logging
import os
import platform
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Callable, Deque, List, Optional

import mss
from PIL import Image

from api_models import create_model

logger = logging.getLogger(__name__)


@dataclass
class VisualEntry:
    timestamp: datetime
    task: str
    app: str
    technical_context: str
    is_deep_work: bool
    image_path: str

    def to_dict(self) -> dict:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


class VisualMonitor:
    """Captures screenshots, labels them with Gemini, stores metadata in a ring buffer."""

    SYSTEM_PROMPT = (
        "You are DevScope, the visual cortex for an engineering team. "
        "For every screenshot you receive, classify the developer's state. "
        "Respond with compact JSON of the form:\n"
        '{"task": "...", "app": "...", "technical_context": "...", "is_deep_work": true}\n'
        "Use short phrases (<=6 words). Detect IDEs, terminals, docs, and distractions."
    )

    def __init__(
        self,
        capture_interval: int = 10,
        max_entries: int = 180,
        temp_dir: Optional[str] = None,
        model_name: str = "gemini-2.0-flash",
        privacy_filter: Optional[Callable[[], bool]] = None,
        on_entry: Optional[Callable[[VisualEntry], None]] = None,
    ):
        self.capture_interval = capture_interval
        self.buffer: Deque[VisualEntry] = deque(maxlen=max_entries)
        self.temp_dir = temp_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp_disk")
        os.makedirs(self.temp_dir, exist_ok=True)
        self.model = create_model(model_name)
        self.privacy_filter = privacy_filter or default_privacy_filter()
        self.on_entry = on_entry
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    # Public API -----------------------------------------------------------

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
        self._cleanup_all_images()
        logger.info("VisualMonitor stopped.")

    def snapshot(self) -> List[VisualEntry]:
        with self._lock:
            return list(self.buffer)

    # Internal helpers ----------------------------------------------------

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                if self.privacy_filter and not self.privacy_filter():
                    logger.debug("Privacy filter blocked capture.")
                    time.sleep(self.capture_interval)
                    continue

                image_path = self._capture_frame()
                if not image_path:
                    time.sleep(self.capture_interval)
                    continue

                metadata = self._label_frame(image_path)
                entry = VisualEntry(
                    timestamp=datetime.utcnow(),
                    task=metadata.get("task", "Unknown"),
                    app=metadata.get("app", "Unknown"),
                    technical_context=metadata.get("technical_context", "N/A"),
                    is_deep_work=bool(metadata.get("is_deep_work", False)),
                    image_path=image_path,
                )
                self._append_entry(entry)
                if self.on_entry:
                    self.on_entry(entry)
            except Exception as exc:
                logger.exception("Monitor loop error: %s", exc)
            finally:
                time.sleep(self.capture_interval)

    def _capture_frame(self) -> Optional[str]:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        file_path = os.path.join(self.temp_dir, f"frame_{timestamp}.png")

        with mss.mss() as sct:
            monitor = sct.monitors[0]  # full virtual screen
            raw = sct.grab(monitor)
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
            img.save(file_path)
            logger.debug("Captured frame %s", file_path)
            return file_path

    def _label_frame(self, image_path: str) -> dict:
        prompt = (
            "Describe the active engineering task, IDE/app name, and any visible clues "
            "like error codes or file names. Output valid JSON only."
        )
        response = self.model.call_model(user_prompt=prompt, system_prompt=self.SYSTEM_PROMPT, image_paths=[image_path])
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

    def _append_entry(self, entry: VisualEntry) -> None:
        with self._lock:
            if len(self.buffer) == self.buffer.maxlen:
                oldest = self.buffer.popleft()
                self._delete_file(oldest.image_path)
            self.buffer.append(entry)
        logger.info(
            "Buffered frame - task=%s app=%s deep_work=%s",
            entry.task,
            entry.app,
            entry.is_deep_work,
        )

    def _cleanup_all_images(self) -> None:
        with self._lock:
            while self.buffer:
                entry = self.buffer.popleft()
                self._delete_file(entry.image_path)

    def _delete_file(self, path: str) -> None:
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError as exc:
            logger.debug("Failed to delete %s: %s", path, exc)


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


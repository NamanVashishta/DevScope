import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from api_models import create_model
from monitor import VisualMonitor, VisualEntry

logger = logging.getLogger(__name__)


class ContextReporter:
    """Renders the recent buffer into a Markdown context report + AI PR draft."""

    PROMPT = (
        "You are an Engineering Scribe. Here is the visual history of a coding session ending in a commit. "
        "Write a structured Pull Request description. List the Files Modified (inferred from context), "
        "the External Docs referenced, and the specific Errors debugged."
    )

    def __init__(
        self,
        monitor: VisualMonitor,
        repo_path: str,
        session_id: str,
        *,
        model_name: str = "gemini-2.0-flash",
        window_minutes: int = 30,
    ):
        self.monitor = monitor
        self.repo_path = Path(repo_path)
        self.session_id = session_id
        self.output_dir = self.repo_path / ".devscope"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.window_minutes = window_minutes
        self.model = create_model(model_name)

    def write_report(self, commit_hash: str) -> Path:
        entries = self.monitor.get_active_buffer(session_id=self.session_id, window_minutes=self.window_minutes)
        if not entries:
            logger.info("No recent buffer entries, skipping context report.")
            return Path()

        timeline_lines = self._format_timeline(entries)
        timeline_text = "\n".join(timeline_lines)
        ai_summary = self._summarize_with_gemini(timeline_text)

        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        file_path = self.output_dir / f"commit_context_{timestamp}.md"

        session = self.monitor.get_session(self.session_id)
        session_label = session.session_name if session else self.session_id

        lines = [
            "# DevScope Commit Context",
            f"- Session: `{session_label}`",
            f"- Commit: `{commit_hash}`",
            f"- Repo: `{self.repo_path.name}`",
            f"- Generated: {datetime.utcnow().isoformat()}Z",
            f"- Lookback Window: last {self.window_minutes} minutes ({len(entries)} frames)",
            "",
            "## Visual Timeline",
        ]
        lines.extend(f"- {line}" for line in timeline_lines)
        lines.extend(
            [
                "",
                "## AI Pull Request Draft",
                ai_summary or "_Gemini summary unavailable._",
            ]
        )

        file_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Context report written to %s", file_path)
        return file_path

    @staticmethod
    def _format_timeline(entries: list[VisualEntry]) -> list[str]:
        formatted = []
        for entry in entries:
            formatted.append(
                f"{entry.timestamp.isoformat()}Z | app={entry.app} | task={entry.task} | "
                f"context={entry.technical_context} | window=\"{entry.window_title}\" | deep_work={entry.is_deep_work}"
            )
        return formatted or ["_No visual events captured._"]

    def _summarize_with_gemini(self, timeline: str) -> str:
        if not timeline.strip():
            return ""
        prompt = f"Visual Timeline:\n{timeline}\n\nProvide the PR description now."
        try:
            response = self.model.call_model(user_prompt=prompt, system_prompt=self.PROMPT)
            return response.strip()
        except Exception as exc:
            logger.warning("Gemini summary failed: %s", exc)
            return ""


class GitTrigger(FileSystemEventHandler):
    """Watches .git/logs/HEAD and emits context reports on commits."""

    def __init__(
        self,
        repo_path: str,
        session_id: str,
        monitor: VisualMonitor,
        status_callback: Optional[Callable[[str], None]] = None,
    ):
        self.repo_path = Path(repo_path)
        self.monitor = monitor
        self.session_id = session_id
        self.reporter = ContextReporter(monitor, repo_path, session_id)
        self.status_callback = status_callback
        self.head_log = self.repo_path / ".git" / "logs" / "HEAD"
        self.observer = Observer()

    def start(self) -> None:
        if not self.head_log.exists():
            raise FileNotFoundError(f"Cannot find {self.head_log}")
        logs_dir = self.head_log.parent
        self.observer.schedule(self, str(logs_dir), recursive=False)
        self.observer.start()
        self._status("Git trigger watching %s" % self.head_log)

    def stop(self) -> None:
        self.observer.stop()
        self.observer.join(timeout=5)
        self._status("Git trigger stopped.")

    def on_modified(self, event) -> None:
        if Path(event.src_path) != self.head_log:
            return
        commit_hash = self._read_latest_hash()
        if not commit_hash:
            return
        report_path = self.reporter.write_report(commit_hash)
        if report_path:
            self._status(f"Context report saved: {report_path.name}")

    def _read_latest_hash(self) -> str:
        try:
            with self.head_log.open("r", encoding="utf-8") as file:
                lines = file.read().strip().splitlines()
                if not lines:
                    return ""
                last_line = lines[-1]
                parts = last_line.split()
                if len(parts) < 2:
                    return ""
                return parts[1]
        except OSError as exc:
            logger.warning("Failed to read HEAD log: %s", exc)
            return ""

    def _status(self, message: str) -> None:
        logger.info(message)
        if self.status_callback:
            self.status_callback(message)


class SlackWatcher:
    """Polls Slack DMs and auto-responds when the buffer shows deep work."""

    def __init__(
        self,
        monitor: VisualMonitor,
        slack_token: str,
        model_name: str = "gemini-2.0-flash",
        poll_interval: int = 8,
        min_deepwork_entries: int = 3,
        status_callback: Optional[Callable[[str], None]] = None,
    ):
        self.monitor = monitor
        self.client = WebClient(token=slack_token)
        self.model = create_model(model_name)
        self.poll_interval = poll_interval
        self.min_deepwork_entries = min_deepwork_entries
        self.status_callback = status_callback
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._latest_ts = {}
        auth = self.client.auth_test()
        self.bot_user_id = auth["user_id"]

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="SlackWatcher", daemon=True)
        self._thread.start()
        self._status("Slack watcher running.")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=self.poll_interval + 2)
        self._status("Slack watcher stopped.")

    # Internal -------------------------------------------------------------

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._poll_dms()
            except SlackApiError as exc:
                self._status(f"Slack error: {exc.response['error']}")
            except Exception as exc:
                logger.exception("Slack watcher failure: %s", exc)
            finally:
                time.sleep(self.poll_interval)

    def _poll_dms(self) -> None:
        channels = self.client.conversations_list(types="im")["channels"]
        for channel in channels:
            cid = channel["id"]
            latest_ts = self._latest_ts.get(cid, "0")
            history = self.client.conversations_history(channel=cid, oldest=latest_ts)
            messages = history.get("messages", [])
            for message in reversed(messages):
                ts = message["ts"]
                if message.get("user") == self.bot_user_id:
                    continue
                if ts <= latest_ts:
                    continue
                self._latest_ts[cid] = ts
                text = message.get("text", "")
                self._handle_question(channel_id=cid, question=text)

    def _handle_question(self, channel_id: str, question: str) -> None:
        if not self._in_deep_work():
            self._status("Skipping auto-reply (not in deep work).")
            return

        context = self._buffer_summary()
        prompt = (
            "You are DevScope, answering Slack questions using visual history. "
            "Question:\n"
            f"{question}\n\n"
            "Context:\n"
            f"{context}\n\n"
            "Respond with the best possible answer if the context is sufficient. "
            "If you cannot answer, reply with exactly 'UNSURE'."
        )

        response = self.model.call_model(user_prompt=prompt, system_prompt="DevScope Slack Auto-Responder")
        reply = response.strip()
        if reply.upper().startswith("UNSURE"):
            self._status("Gemini unsure; not replying.")
            return

        self.client.chat_postMessage(channel=channel_id, text=reply)
        self._status("Auto-replied on Slack.")

    def _in_deep_work(self) -> bool:
        entries = self.monitor.snapshot()
        if len(entries) < self.min_deepwork_entries:
            return False
        recent = entries[-self.min_deepwork_entries :]
        return all(entry.is_deep_work for entry in recent)

    def _buffer_summary(self) -> str:
        entries = self.monitor.snapshot()
        if not entries:
            return "No visual history available."

        lines = []
        for entry in entries[-6:]:
            lines.append(
                f"{entry.timestamp.isoformat()} | {entry.app} | {entry.task} | {entry.technical_context}"
            )
        return "\n".join(lines)

    def _status(self, message: str) -> None:
        logger.info(message)
        if self.status_callback:
            self.status_callback(message)


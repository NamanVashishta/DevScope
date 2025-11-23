import json
import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from api_models import create_model
from activity_schema import ActivityRecord
from monitor import VisualMonitor

logger = logging.getLogger(__name__)


class ContextReporter:
    """Renders the recent buffer into a Markdown context report + AI PR draft."""

    PROMPT = (
        "You are the DevScope Smart Extractor for git commits. Using the structured timeline, write a Pull "
        "Request description that explicitly calls out: (1) files/functions touched, (2) exact error codes "
        "or stack traces resolved, (3) documentation or research URLs referenced, and (4) remaining risks. "
        "Organize the response under headings: Summary, Files & Functions, Errors Fixed, Docs & Research, "
        "Open Questions."
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

        session = self.monitor.get_session(self.session_id)
        timeline_lines = self._format_timeline(entries)
        timeline_text = "\n".join(timeline_lines)
        goal = session.goal if session else ""
        ai_summary = self._summarize_with_gemini(timeline_text, session_goal=goal)

        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        file_path = self.output_dir / f"commit_context_{timestamp}.md"

        session_label = session.goal if session else self.session_id

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
        lines.extend(["", "## Structured Event Table", ""])
        lines.extend(self._format_structured_table(entries))
        lines.extend(["", "## Raw Activity Records"])
        for block in self._format_raw_records(entries):
            lines.append("```json")
            lines.append(block)
            lines.append("```")

        file_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Context report written to %s", file_path)
        return file_path

    @staticmethod
    def _format_timeline(entries: list[ActivityRecord]) -> list[str]:
        formatted = []
        for entry in entries:
            line = (
                f"{entry.timestamp.isoformat()}Z | type={entry.activity_type} | task={entry.task} | "
                f"context={entry.technical_context} | error={entry.error_code or 'n/a'} | "
                f"function={entry.function_target or 'n/a'} | doc={entry.documentation_title or 'n/a'} | "
                f"app={entry.app_name} | focus_app={entry.active_app} | window=\"{entry.window_title}\" | "
                f"deep_state={entry.deep_work_state}"
            )
            if entry.doc_url:
                line += f" | doc_url={entry.doc_url}"
            formatted.append(line)
        return formatted or ["_No visual events captured._"]

    @staticmethod
    def _format_structured_table(entries: list[ActivityRecord]) -> list[str]:
        rows: list[str] = []
        for entry in entries:
            rows.append(
                f"- **{entry.timestamp.isoformat()}Z** — {entry.activity_type} :: {entry.task}\n"
                f"  - Context: {entry.technical_context}\n"
                f"  - Error: {entry.error_code or 'n/a'} | Function: {entry.function_target or 'n/a'}\n"
                f"  - Docs: {entry.documentation_title or 'n/a'} ({entry.doc_url or 'n/a'})\n"
                f"  - Apps: LLM={entry.app_name}, Focus={entry.active_app}\n"
                f"  - Privacy: {entry.privacy_state} / {entry.deep_work_state}\n"
            )
        return rows or ["_No structured data available._"]

    @staticmethod
    def _format_raw_records(entries: list[ActivityRecord]) -> list[str]:
        blocks: list[str] = []
        for entry in entries:
            payload = entry.to_payload()
            timestamp = payload.get("timestamp")
            if hasattr(timestamp, "isoformat"):
                payload["timestamp"] = timestamp.isoformat()
            blocks.append(json.dumps(payload, indent=2, default=str))
        return blocks

    def _summarize_with_gemini(self, timeline: str, session_goal: str = "") -> str:
        if not timeline.strip():
            return ""
        prompt = (
            f"Visual Timeline:\n{timeline}\n\n"
            f"Session goal: {session_goal or 'Unknown'}\n\n"
            "Provide the pull request summary now."
        )
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



import unittest
from datetime import datetime, timedelta
from unittest import mock

from activity_schema import ActivityRecord
from monitor import VisualMonitor


class MonitorBufferTests(unittest.TestCase):
    def setUp(self) -> None:
        patcher = mock.patch("monitor.create_model", autospec=True)
        self.addCleanup(patcher.stop)
        fake_create_model = patcher.start()
        fake_create_model.return_value = mock.Mock()
        self.monitor = VisualMonitor(capture_interval=1, max_entries=10)
        self.session = self.monitor.create_session("Test Project", "/tmp", "Ship it")

    def test_active_buffer_filters_by_time_and_privacy(self) -> None:
        now = datetime.utcnow()
        allowed_recent = self._record(now - timedelta(minutes=5), is_deep=True, privacy_state="allowed")
        blocked_recent = self._record(now - timedelta(minutes=3), is_deep=False, privacy_state="blocked")
        old_allowed = self._record(now - timedelta(minutes=45), is_deep=True, privacy_state="allowed")

        self.session.ring_buffer.extend([old_allowed, blocked_recent, allowed_recent])

        window_entries = self.monitor.get_active_buffer(session_id=self.session.id, window_minutes=30)

        self.assertEqual(len(window_entries), 1)
        self.assertEqual(window_entries[0].task, allowed_recent.task)

    def _record(self, timestamp: datetime, *, is_deep: bool, privacy_state: str) -> ActivityRecord:
        return ActivityRecord(
            timestamp=timestamp,
            session_id=self.session.id,
            project_name=self.session.project_name,
            project_slug=self.session.project_slug,
            session_goal=self.session.goal,
            repo_path=self.session.repo_path,
            task="Test Task",
            activity_type="CODING",
            technical_context="monitor.py > capture",
            app_name="VS Code",
            active_app="VS Code",
            window_title="monitor.py — VS Code",
            alignment_score=90,
            is_deep_work=is_deep,
            deep_work_state="deep_work" if is_deep else "distracted",
            privacy_state=privacy_state,
        )


if __name__ == "__main__":
    unittest.main()


import html
import os
import sys
import threading
from pathlib import Path
from typing import List, Optional

from PyQt5 import QtCore, QtGui, QtWidgets
from qt_material import apply_stylesheet

from db import HiveMindClient
from monitor import VisualMonitor, VisualEntry
from oracle import OracleService
from settings_store import load_settings, save_settings
from triggers import GitTrigger, SlackWatcher


class SignalBus(QtCore.QObject):
    log = QtCore.pyqtSignal(str)
    buffer = QtCore.pyqtSignal(list)
    state = QtCore.pyqtSignal(str)
    oracle_answer = QtCore.pyqtSignal(str)
    oracle_status = QtCore.pyqtSignal(str)


class DevScopeWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DevScope – Visual Cortex")
        self.setMinimumSize(960, 640)

        self.identity = load_settings()
        self.hivemind_client = HiveMindClient()
        self.oracle_service = OracleService(self.hivemind_client)
        self.monitor: VisualMonitor | None = VisualMonitor(
            capture_interval=10,
            on_entry=self._handle_entry,
            hivemind_client=self.hivemind_client,
        )
        self._apply_identity_to_systems()
        self._monitor_running = False
        self.git_trigger: GitTrigger | None = None
        self.slack_watcher: SlackWatcher | None = None

        self.bus = SignalBus()
        self.bus.log.connect(self._append_log)
        self.bus.buffer.connect(self._render_buffer)
        self.bus.state.connect(self._update_status)
        self.bus.oracle_answer.connect(self._render_oracle_answer)
        self.bus.oracle_status.connect(self._update_oracle_status)

        self._session_running = False

        self._build_layout()
        self._refresh_session_combo()

    # UI ------------------------------------------------------------------

    def _build_layout(self) -> None:
        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header row
        header_layout = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("DevScope")
        title.setFont(QtGui.QFont("Inter", 28, QtGui.QFont.Bold))
        subtitle = QtWidgets.QLabel("The Visual Cortex for Engineering Teams")
        subtitle.setFont(QtGui.QFont("Inter", 12))
        subtitle.setStyleSheet("color: #9fbccf;")

        title_block = QtWidgets.QVBoxLayout()
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        header_layout.addLayout(title_block)
        header_layout.addStretch()

        self.settings_btn = QtWidgets.QPushButton("Settings")
        self.settings_btn.clicked.connect(self._open_settings_dialog)
        header_layout.addWidget(self.settings_btn)

        self.status_chip = QtWidgets.QLabel("Idle")
        self.status_chip.setAlignment(QtCore.Qt.AlignCenter)
        self.status_chip.setFixedWidth(120)
        self.status_chip.setStyleSheet("border-radius: 16px; padding: 8px 12px; background-color: #4a5568; color: white;")
        header_layout.addWidget(self.status_chip)

        layout.addLayout(header_layout)

        self.tab_widget = QtWidgets.QTabWidget()
        self.tab_widget.addTab(self._build_mission_control_tab(), "Mission Control")
        self.tab_widget.addTab(self._build_hive_mind_tab(), "Hive Mind")
        layout.addWidget(self.tab_widget)

        central.setLayout(layout)
        self.setCentralWidget(central)

    def _build_mission_control_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)

        session_bar = QtWidgets.QHBoxLayout()
        session_label = QtWidgets.QLabel("Sessions")
        session_label.setFont(QtGui.QFont("Inter", 12, QtGui.QFont.Bold))
        self.session_combo = QtWidgets.QComboBox()
        self.session_combo.currentIndexChanged.connect(self._handle_session_combo_change)
        self.new_session_btn = QtWidgets.QPushButton("＋ New Session")
        self.new_session_btn.clicked.connect(self._open_new_session_dialog)
        self.delete_session_btn = QtWidgets.QPushButton("🗑")
        self.delete_session_btn.clicked.connect(self._delete_current_session)
        self.delete_session_btn.setToolTip("Delete selected session")

        session_bar.addWidget(session_label)
        session_bar.addWidget(self.session_combo, 1)
        session_bar.addWidget(self.new_session_btn)
        session_bar.addWidget(self.delete_session_btn)
        layout.addLayout(session_bar)

        # Controls
        controls = QtWidgets.QHBoxLayout()
        self.start_btn = QtWidgets.QPushButton("Start Session")
        self.start_btn.setMinimumHeight(48)
        self.start_btn.clicked.connect(self._start_session)

        self.stop_btn = QtWidgets.QPushButton("Stop Session")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setMinimumHeight(48)
        self.stop_btn.clicked.connect(self._stop_session)

        controls.addWidget(self.start_btn)
        controls.addWidget(self.stop_btn)
        layout.addLayout(controls)

        # Buffer table
        buffer_label = QtWidgets.QLabel("Visual Ring Buffer (latest 10)")
        buffer_label.setFont(QtGui.QFont("Inter", 14, QtGui.QFont.Bold))
        layout.addWidget(buffer_label)

        self.buffer_table = QtWidgets.QTableWidget(0, 4)
        self.buffer_table.setHorizontalHeaderLabels(["Timestamp", "App", "Task", "Deep Work"])
        self.buffer_table.horizontalHeader().setStretchLastSection(True)
        self.buffer_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.buffer_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.buffer_table)

        # Log panel
        log_label = QtWidgets.QLabel("Live Status Log")
        log_label.setFont(QtGui.QFont("Inter", 14, QtGui.QFont.Bold))
        layout.addWidget(log_label)

        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(500)
        layout.addWidget(self.log_view)

        return widget

    def _build_hive_mind_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)

        intro = QtWidgets.QLabel("Ask the Hive Mind about your entire organization's work history.")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.oracle_chat_view = QtWidgets.QTextBrowser()
        self.oracle_chat_view.setOpenExternalLinks(True)
        layout.addWidget(self.oracle_chat_view, 1)

        input_row = QtWidgets.QHBoxLayout()
        self.oracle_question_input = QtWidgets.QLineEdit()
        self.oracle_question_input.setPlaceholderText("e.g., What was Alice working on yesterday?")
        self.oracle_question_input.returnPressed.connect(self._handle_oracle_question)
        input_row.addWidget(self.oracle_question_input, 1)

        self.ask_oracle_btn = QtWidgets.QPushButton("Ask Question")
        self.ask_oracle_btn.setMinimumHeight(36)
        self.ask_oracle_btn.clicked.connect(self._handle_oracle_question)
        input_row.addWidget(self.ask_oracle_btn)

        self.oracle_status_label = QtWidgets.QLabel("Idle")
        self.oracle_status_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        input_row.addWidget(self.oracle_status_label)
        layout.addLayout(input_row)

        return widget

    # Actions -------------------------------------------------------------

    def _current_session_id(self) -> Optional[str]:
        data = self.session_combo.currentData()
        return data if isinstance(data, str) else None

    def _start_session(self) -> None:
        session_id = self._current_session_id()
        if not session_id:
            QtWidgets.QMessageBox.warning(self, "Select Session", "Create or select a session before starting.")
            return

        if self._session_running:
            return

        try:
            self.monitor.switch_session(session_id)
        except ValueError as exc:
            QtWidgets.QMessageBox.critical(self, "Session Error", str(exc))
            return

        try:
            if not self.monitor.is_running():
                self.monitor.start()
            self._monitor_running = True
            self._start_git_trigger_for_session(session_id)

            slack_token = os.environ.get("SLACK_BOT_TOKEN")
            if slack_token:
                self.slack_watcher = SlackWatcher(
                    monitor=self.monitor,
                    slack_token=slack_token,
                    status_callback=self._log_async,
                )
                self.slack_watcher.start()
            else:
                self._log_async("SLACK_BOT_TOKEN not set; Slack watcher disabled.")

            self._session_running = True
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.bus.state.emit("Running")
            self._log_async("DevScope session started.")
        except Exception as exc:
            self._log_async(f"Failed to start session: {exc}")
            QtWidgets.QMessageBox.critical(self, "Error", str(exc))
            self._stop_session()

    def _stop_session(self) -> None:
        if self.slack_watcher:
            self.slack_watcher.stop()
            self.slack_watcher = None
        if self.git_trigger:
            self.git_trigger.stop()
            self.git_trigger = None
        if self.monitor and self.monitor.is_running():
            self.monitor.stop()
        self._monitor_running = False

        self._session_running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.bus.state.emit("Idle")
        self._log_async("DevScope session stopped.")

    def closeEvent(self, event) -> None:
        self._stop_session()
        super().closeEvent(event)

    # Callbacks -----------------------------------------------------------

    def _handle_entry(self, entry: VisualEntry) -> None:
        if not self.monitor:
            return
        active_id = self.monitor.get_active_session_id()
        if not active_id or entry.session_id != active_id:
            return

        entries = [e.to_dict() for e in self.monitor.snapshot(active_id)]
        self.bus.buffer.emit(entries)
        self.bus.log.emit(
            f"[{entry.active_app}] {entry.task} | {entry.app} | deep_work={entry.is_deep_work}"
        )

    def _append_log(self, text: str) -> None:
        self.log_view.appendPlainText(text)
        self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())

    def _render_buffer(self, entries: List[dict]) -> None:
        latest = entries[-10:]
        self.buffer_table.setRowCount(len(latest))
        for row, entry in enumerate(reversed(latest)):
            self.buffer_table.setItem(row, 0, QtWidgets.QTableWidgetItem(entry["timestamp"]))
            self.buffer_table.setItem(row, 1, QtWidgets.QTableWidgetItem(entry["app"]))
            self.buffer_table.setItem(row, 2, QtWidgets.QTableWidgetItem(entry["task"]))
            deep_item = QtWidgets.QTableWidgetItem("Yes" if entry["is_deep_work"] else "No")
            deep_item.setForeground(QtGui.QColor("#10b981" if entry["is_deep_work"] else "#f87171"))
            self.buffer_table.setItem(row, 3, deep_item)

    def _update_status(self, state: str) -> None:
        color = "#10b981" if state == "Running" else "#4a5568"
        self.status_chip.setText(state)
        self.status_chip.setStyleSheet(f"border-radius: 16px; padding: 8px 12px; background-color: {color}; color: white;")

    def _log_async(self, text: str) -> None:
        self.bus.log.emit(text)

    def _apply_identity_to_systems(self) -> None:
        """Propagate identity settings to the monitor and other services."""
        identity = self.identity or {}
        if self.monitor:
            self.monitor.update_identity(
                user_id=identity.get("username"),
                org_id=identity.get("organization_id"),
                project_name=identity.get("project_name"),
                display_name=identity.get("username"),
            )

    def _open_settings_dialog(self) -> None:
        dialog = SettingsDialog(self.identity, self)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return
        self.identity = dialog.values()
        save_settings(self.identity)
        self._apply_identity_to_systems()
        self._log_async("Identity settings updated.")

    # Oracle interactions --------------------------------------------------

    def _handle_oracle_question(self) -> None:
        if not self.oracle_service:
            QtWidgets.QMessageBox.warning(self, "Hive Mind Disabled", "Oracle is not configured.")
            return

        question = self.oracle_question_input.text().strip()
        if not question:
            QtWidgets.QMessageBox.warning(self, "Missing Question", "Enter a question for the Hive Mind.")
            return

        org_id = self.identity.get("organization_id")
        if not org_id:
            QtWidgets.QMessageBox.warning(self, "Set Organization", "Open Settings and add your Organization ID.")
            return

        self.ask_oracle_btn.setEnabled(False)
        self.oracle_status_label.setText("Querying Hive Mind…")
        self._append_chat_line("You", question)
        self.oracle_question_input.clear()
        thread = threading.Thread(
            target=self._run_oracle_query,
            args=(question, org_id, None),
            daemon=True,
        )
        thread.start()

    def _run_oracle_query(self, question: str, org_id: str, project_name: Optional[str]) -> None:
        self.bus.oracle_status.emit("Querying Hive Mind…")
        answer = self.oracle_service.ask(question, org_id=org_id, project_name=project_name)
        self.bus.oracle_answer.emit(answer)
        self.bus.oracle_status.emit("Idle")

    def _render_oracle_answer(self, answer: str) -> None:
        if hasattr(self, "oracle_chat_view"):
            self._append_chat_line("Oracle", answer)
        if hasattr(self, "ask_oracle_btn"):
            self.ask_oracle_btn.setEnabled(True)

    def _update_oracle_status(self, status: str) -> None:
        if hasattr(self, "oracle_status_label"):
            self.oracle_status_label.setText(status)
        if status.lower().startswith("querying") and hasattr(self, "ask_oracle_btn"):
            self.ask_oracle_btn.setEnabled(False)
        elif status == "Idle" and hasattr(self, "ask_oracle_btn"):
            self.ask_oracle_btn.setEnabled(True)

    def _append_chat_line(self, speaker: str, message: str) -> None:
        if not hasattr(self, "oracle_chat_view"):
            return
        safe_speaker = html.escape(speaker)
        safe_message = html.escape(message)
        self.oracle_chat_view.append(f"<b>{safe_speaker}:</b> {safe_message}")

    # Session management helpers -----------------------------------------

    def _open_new_session_dialog(self) -> None:
        dialog = NewSessionDialog(self)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return
        goal, repo_path = dialog.values()
        if not goal or not repo_path:
            QtWidgets.QMessageBox.warning(self, "Missing Data", "Provide both goal and repository path.")
            return
        if not os.path.isdir(os.path.join(repo_path, ".git")):
            QtWidgets.QMessageBox.warning(self, "Invalid Repo", "Selected folder does not contain a .git directory.")
            return

        session = self.monitor.create_session(name=goal, repo_path=repo_path, goal=goal)
        self._log_async(f"Session '{goal}' created.")
        self._refresh_session_combo(select_id=session.id)
        if self._monitor_running:
            self._switch_to_session(session.id, clear_log=True)

    def _delete_current_session(self) -> None:
        session_id = self._current_session_id()
        if not session_id:
            return

        if QtWidgets.QMessageBox.question(
            self,
            "Delete Session",
            "Delete the selected session?",
        ) != QtWidgets.QMessageBox.Yes:
            return

        if self.git_trigger:
            self.git_trigger.stop()
            self.git_trigger = None

        self.monitor.delete_session(session_id)
        self._log_async("Session deleted.")
        self._refresh_session_combo()

        new_session_id = self._current_session_id()
        if self._monitor_running and new_session_id:
            self._switch_to_session(new_session_id, clear_log=True)
        elif self._monitor_running and not new_session_id:
            self._stop_session()

    def _refresh_session_combo(self, select_id: Optional[str] = None) -> None:
        metadata = self.monitor.get_sessions_metadata()
        self.session_combo.blockSignals(True)
        self.session_combo.clear()

        for meta in metadata:
            label = f"{meta['name']} ({Path(meta['repo_path']).name})"
            self.session_combo.addItem(label, meta["id"])

        if not metadata:
            self.session_combo.addItem("No sessions", None)
            self.session_combo.setCurrentIndex(0)
            self.session_combo.blockSignals(False)
            self.delete_session_btn.setEnabled(False)
            self.start_btn.setEnabled(False)
            return

        target_id = select_id or metadata[0]["id"]
        index = next((i for i, meta in enumerate(metadata) if meta["id"] == target_id), 0)
        self.session_combo.setCurrentIndex(index)
        self.session_combo.blockSignals(False)
        self.delete_session_btn.setEnabled(True)
        if not self._session_running:
            self.start_btn.setEnabled(True)
        self._switch_to_session(self.session_combo.itemData(index), clear_log=True)

    def _handle_session_combo_change(self, index: int) -> None:
        session_id = self.session_combo.itemData(index)
        if not session_id:
            return
        self._switch_to_session(session_id, clear_log=True)

    def _switch_to_session(self, session_id: str, clear_log: bool = False) -> None:
        if not session_id:
            return
        try:
            self.monitor.switch_session(session_id)
        except ValueError as exc:
            self._log_async(str(exc))
            return

        if clear_log:
            self.log_view.clear()
            self.buffer_table.setRowCount(0)

        if self._monitor_running:
            self._start_git_trigger_for_session(session_id)

    def _start_git_trigger_for_session(self, session_id: str) -> None:
        session = self.monitor.get_session(session_id)
        if not session:
            self._log_async("Cannot start git watcher: session missing.")
            return
        repo = session.repo_path
        if not os.path.isdir(os.path.join(repo, ".git")):
            self._log_async("Cannot start git watcher: repo missing .git directory.")
            return

        if self.git_trigger:
            self.git_trigger.stop()
            self.git_trigger = None

        self.git_trigger = GitTrigger(
            repo_path=repo,
            session_id=session_id,
            monitor=self.monitor,
            status_callback=self._log_async,
        )
        self.git_trigger.start()


class NewSessionDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Session")
        self.setModal(True)
        layout = QtWidgets.QFormLayout(self)

        self.goal_input = QtWidgets.QLineEdit()
        layout.addRow("Session Name / Goal", self.goal_input)

        repo_layout = QtWidgets.QHBoxLayout()
        self.repo_input = QtWidgets.QLineEdit()
        browse_btn = QtWidgets.QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_repo)
        repo_layout.addWidget(self.repo_input)
        repo_layout.addWidget(browse_btn)
        layout.addRow("Repository Path", repo_layout)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _browse_repo(self) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select repository")
        if path:
            self.repo_input.setText(path)

    def values(self) -> tuple[str, str]:
        return self.goal_input.text().strip(), self.repo_input.text().strip()


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DevScope Settings")
        self.setModal(True)

        layout = QtWidgets.QFormLayout(self)
        self.username_input = QtWidgets.QLineEdit(settings.get("username", ""))
        layout.addRow("Username", self.username_input)

        self.org_input = QtWidgets.QLineEdit(settings.get("organization_id", ""))
        layout.addRow("Organization ID", self.org_input)

        self.project_input = QtWidgets.QLineEdit(settings.get("project_name", ""))
        layout.addRow("Current Project", self.project_input)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def values(self) -> dict:
        return {
            "username": self.username_input.text().strip(),
            "organization_id": self.org_input.text().strip(),
            "project_name": self.project_input.text().strip(),
        }

def main():
    app = QtWidgets.QApplication(sys.argv)
    apply_stylesheet(app, theme="dark_teal.xml")
    window = DevScopeWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()


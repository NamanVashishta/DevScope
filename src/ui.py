import os
import sys
from typing import List

from PyQt5 import QtCore, QtGui, QtWidgets
from qt_material import apply_stylesheet

from monitor import VisualMonitor, VisualEntry
from triggers import GitTrigger, SlackWatcher


class SignalBus(QtCore.QObject):
    log = QtCore.pyqtSignal(str)
    buffer = QtCore.pyqtSignal(list)
    state = QtCore.pyqtSignal(str)


class DevScopeWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DevScope – Visual Cortex")
        self.setMinimumSize(960, 640)

        self.monitor: VisualMonitor | None = None
        self.git_trigger: GitTrigger | None = None
        self.slack_watcher: SlackWatcher | None = None
        self.repo_path: str | None = None

        self.bus = SignalBus()
        self.bus.log.connect(self._append_log)
        self.bus.buffer.connect(self._render_buffer)
        self.bus.state.connect(self._update_status)

        self._session_running = False

        self._build_layout()

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

        self.status_chip = QtWidgets.QLabel("Idle")
        self.status_chip.setAlignment(QtCore.Qt.AlignCenter)
        self.status_chip.setFixedWidth(120)
        self.status_chip.setStyleSheet("border-radius: 16px; padding: 8px 12px; background-color: #4a5568; color: white;")
        header_layout.addWidget(self.status_chip)

        layout.addLayout(header_layout)

        # Repo picker
        repo_layout = QtWidgets.QHBoxLayout()
        self.repo_input = QtWidgets.QLineEdit()
        self.repo_input.setPlaceholderText("Select repository folder...")
        browse_btn = QtWidgets.QPushButton("Select Project Folder")
        browse_btn.clicked.connect(self._choose_repo)

        repo_layout.addWidget(self.repo_input)
        repo_layout.addWidget(browse_btn)
        layout.addLayout(repo_layout)

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

        central.setLayout(layout)
        self.setCentralWidget(central)

    # Actions -------------------------------------------------------------

    def _choose_repo(self) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select repo")
        if path:
            self.repo_input.setText(path)
            self.repo_path = path

    def _start_session(self) -> None:
        repo = self.repo_input.text().strip()
        if not repo:
            QtWidgets.QMessageBox.warning(self, "Select Repo", "Please choose a repository folder.")
            return
        if not os.path.isdir(os.path.join(repo, ".git")):
            QtWidgets.QMessageBox.warning(self, "Not a git repo", "Selected folder does not contain a .git directory.")
            return

        if self._session_running:
            return

        try:
            self.monitor = VisualMonitor(on_entry=self._handle_entry)
            self.monitor.start()

            self.git_trigger = GitTrigger(repo_path=repo, monitor=self.monitor, status_callback=self._log_async)
            self.git_trigger.start()

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
        if self.monitor:
            self.monitor.stop()
            self.monitor = None

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
        entries = []
        if self.monitor:
            entries = [e.to_dict() for e in self.monitor.snapshot()]
        self.bus.buffer.emit(entries)
        self.bus.log.emit(
            f"Frame: {entry.task} | {entry.app} | deep_work={entry.is_deep_work}"
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


def main():
    app = QtWidgets.QApplication(sys.argv)
    apply_stylesheet(app, theme="dark_teal.xml")
    window = DevScopeWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()


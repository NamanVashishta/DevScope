import html
import os
import sys
import threading
from pathlib import Path
from typing import List, Optional

from PyQt5 import QtCore, QtGui, QtWidgets
from qt_material import apply_stylesheet

from activity_schema import ActivityRecord
from db import HiveMindClient
from monitor import VisualMonitor
from oracle import OracleService
from settings_store import load_settings, save_settings
from session_store import load_saved_projects, save_projects_state
from triggers import GitTrigger


class SignalBus(QtCore.QObject):
    log = QtCore.pyqtSignal(str)
    buffer = QtCore.pyqtSignal(list)
    state = QtCore.pyqtSignal(str)
    oracle_answer = QtCore.pyqtSignal(object)
    oracle_status = QtCore.pyqtSignal(str)


class DevScopeWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DevScope")
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
        self._oracle_time_options = [
            ("Last 24h", 24),
            ("Last 72h", 72),
            ("Last 7 days", 168),
            ("All Activity", 0),
        ]
        self.oracle_history: List[dict] = []

        self.bus = SignalBus()
        self.bus.log.connect(self._append_log)
        self.bus.buffer.connect(self._render_buffer)
        self.bus.state.connect(self._update_status)
        self.bus.oracle_answer.connect(self._render_oracle_answer)
        self.bus.oracle_status.connect(self._update_oracle_status)

        self._session_running = False

        self._build_layout()
        self._restore_projects_from_disk()
        self._refresh_session_combo()

    # UI ------------------------------------------------------------------

    def _build_layout(self) -> None:
        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Hero header card
        hero_frame = QtWidgets.QFrame()
        hero_frame.setObjectName("HeroFrame")
        hero_frame.setStyleSheet(
            """
            QFrame#HeroFrame {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #111827,
                    stop:1 #0b1120
                );
                border-radius: 28px;
                border: 1px solid rgba(56, 189, 248, 0.08);
            }
            QLabel#HeroLogo {
                color: #38bdf8;
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 2px;
            }
            QLabel#HeroTitle {
                color: #f8fafc;
                font-size: 30px;
                font-weight: 800;
            }
            QLabel#HeroSubtitle {
                color: #cbd5f5;
                font-size: 13px;
            }
            QFrame#StatCard {
                background-color: rgba(15, 23, 42, 0.6);
                border-radius: 14px;
                border: 1px solid rgba(148, 163, 184, 0.25);
            }
            """
        )
        hero_layout = QtWidgets.QHBoxLayout(hero_frame)
        hero_layout.setContentsMargins(32, 28, 32, 28)
        hero_layout.setSpacing(32)

        left_block = QtWidgets.QVBoxLayout()
        left_block.setSpacing(8)
        title = QtWidgets.QLabel("DevScope")
        title.setObjectName("HeroTitle")
        title.setWordWrap(True)
        left_block.addWidget(title)

        subtitle = QtWidgets.QLabel("Capture every engineering breadcrumb and answer status questions without interruptions.")
        subtitle.setObjectName("HeroSubtitle")
        subtitle.setWordWrap(True)
        left_block.addWidget(subtitle)

        left_block.addSpacing(8)

        hero_layout.addLayout(left_block, stretch=2)

        right_block = QtWidgets.QVBoxLayout()
        right_block.setSpacing(12)
        right_block.setAlignment(QtCore.Qt.AlignTop)

        self.status_chip = QtWidgets.QLabel("Idle")
        self.status_chip.setAlignment(QtCore.Qt.AlignCenter)
        self.status_chip.setFixedWidth(160)
        self.status_chip.setStyleSheet(
            "border-radius: 20px; padding: 10px 18px; background-color: #4b5563; color: #f8fafc; font-weight: 700;"
        )
        right_block.addWidget(self.status_chip, alignment=QtCore.Qt.AlignRight)

        self.settings_btn = QtWidgets.QPushButton("Open Settings")
        self.settings_btn.clicked.connect(self._open_settings_dialog)
        self.settings_btn.setStyleSheet(
            """
            QPushButton {
                border-radius: 16px;
                padding: 12px 22px;
                background-color: #38bdf8;
                color: #0f172a;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #7dd3fc;
            }
            """
        )
        right_block.addWidget(self.settings_btn, alignment=QtCore.Qt.AlignRight)

        hero_layout.addLayout(right_block, stretch=1)
        layout.addWidget(hero_frame)

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
        session_label = QtWidgets.QLabel("Projects / Sessions")
        session_label.setFont(QtGui.QFont("Inter", 12, QtGui.QFont.Bold))
        self.session_combo = QtWidgets.QComboBox()
        self.session_combo.setStyleSheet(
            """
            QComboBox {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #3b82f6;
                border-radius: 10px;
                padding: 6px 10px;
                min-height: 32px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #0f172a;
                color: #e2e8f0;
                selection-background-color: #38bdf8;
                selection-color: #0f172a;
                border-radius: 10px;
                padding: 6px;
            }
            """
        )
        self.session_combo.currentIndexChanged.connect(self._handle_session_combo_change)
        self.session_combo.setPlaceholderText("No sessions yet — add one below")
        self.new_session_btn = QtWidgets.QPushButton("＋ New Session")
        self.new_session_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #0ea5e9;
                color: #0f172a;
                font-weight: 700;
                border-radius: 12px;
                padding: 10px 16px;
            }
            """
        )
        self.new_session_btn.clicked.connect(self._open_new_session_dialog)
        self.delete_session_btn = QtWidgets.QPushButton("🗑")
        self.complete_session_btn = QtWidgets.QPushButton("Complete")
        self.complete_session_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #f59e0b;
                color: #0f172a;
                border-radius: 12px;
                padding: 10px 16px;
                font-weight: 600;
            }
            QPushButton:disabled {
                background-color: #1f2937;
                color: #94a3b8;
            }
            """
        )
        self.complete_session_btn.clicked.connect(self._complete_current_session)
        self.delete_session_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #1e293b;
                color: #f8fafc;
                border-radius: 12px;
                padding: 10px 16px;
            }
            QPushButton:disabled {
                color: #475569;
            }
            """
        )
        self.delete_session_btn.clicked.connect(self._delete_current_session)
        self.delete_session_btn.setToolTip("Delete selected session")

        session_bar.addWidget(session_label)
        session_bar.addWidget(self.session_combo, 1)
        session_bar.addWidget(self.new_session_btn)
        session_bar.addWidget(self.complete_session_btn)
        session_bar.addWidget(self.delete_session_btn)
        layout.addLayout(session_bar)

        # Controls
        controls = QtWidgets.QHBoxLayout()
        self.start_btn = QtWidgets.QPushButton("Start Session")
        self.start_btn.setMinimumHeight(48)
        self.start_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #22c55e;
                color: #0f172a;
                font-weight: 700;
                border-radius: 12px;
            }
            QPushButton:disabled {
                background-color: #1f2937;
                color: #94a3b8;
            }
            """
        )
        self.start_btn.clicked.connect(self._start_session)

        self.stop_btn = QtWidgets.QPushButton("Stop Session")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setMinimumHeight(48)
        self.stop_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #ef4444;
                color: #0f172a;
                font-weight: 700;
                border-radius: 12px;
            }
            QPushButton:disabled {
                background-color: #1f2937;
                color: #94a3b8;
            }
            """
        )
        self.stop_btn.clicked.connect(self._stop_session)

        controls.addWidget(self.start_btn)
        controls.addWidget(self.stop_btn)
        layout.addLayout(controls)

        self.focus_chip = QtWidgets.QLabel("Active Focus: Unknown")
        self.focus_chip.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        self.focus_chip.setStyleSheet(
            "border-radius: 12px; padding: 6px 12px; background-color: #2563eb; color: #f8fafc; font-weight: 600;"
        )
        layout.addWidget(self.focus_chip)

        # Buffer table
        buffer_label = QtWidgets.QLabel("Visual Ring Buffer (latest 10)")
        buffer_label.setFont(QtGui.QFont("Inter", 14, QtGui.QFont.Bold))
        layout.addWidget(buffer_label)

        self.buffer_table = QtWidgets.QTableWidget(0, 7)
        self.buffer_table.setHorizontalHeaderLabels(
            ["Timestamp", "Task", "Activity Type", "LLM App", "Focus App", "Error / Docs", "Privacy"]
        )
        self.buffer_table.setAlternatingRowColors(True)
        self.buffer_table.setStyleSheet(
            """
            QTableWidget {
                background-color: #0f172a;
                alternate-background-color: #1e293b;
                color: #e2e8f0;
                gridline-color: #334155;
            }
            QHeaderView::section {
                background-color: #1d4ed8;
                color: #f8fafc;
                padding: 6px;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #38bdf8;
                color: #0f172a;
            }
            """
        )
        header = self.buffer_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.Interactive)
        self.buffer_table.setColumnWidth(5, 240)
        self.buffer_table.verticalHeader().setVisible(False)
        self.buffer_table.verticalHeader().setDefaultSectionSize(56)
        self.buffer_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.buffer_table.setWordWrap(True)
        layout.addWidget(self.buffer_table)

        # Log panel
        log_label = QtWidgets.QLabel("Live Status Log")
        log_label.setFont(QtGui.QFont("Inter", 14, QtGui.QFont.Bold))
        layout.addWidget(log_label)

        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(500)
        self.log_view.setStyleSheet(
            """
            QPlainTextEdit {
                background-color: #0b1120;
                color: #e2e8f0;
                border-radius: 10px;
                padding: 10px;
            }
            """
        )
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

        filters_frame = QtWidgets.QFrame()
        filters_frame.setObjectName("OracleFilters")
        filters_frame.setStyleSheet(
            """
            QFrame#OracleFilters {
                background-color: #0f172a;
                border-radius: 14px;
                border: 1px solid rgba(56, 189, 248, 0.15);
            }
            """
        )
        filters_layout = QtWidgets.QHBoxLayout(filters_frame)
        filters_layout.setContentsMargins(18, 14, 18, 14)
        filters_layout.setSpacing(18)

        def _build_filter_column(label_text: str, widget_obj: QtWidgets.QWidget) -> QtWidgets.QVBoxLayout:
            column = QtWidgets.QVBoxLayout()
            label = QtWidgets.QLabel(label_text)
            label.setStyleSheet("color: #93c5fd; font-weight: 600;")
            column.addWidget(label)
            column.addWidget(widget_obj)
            return column

        self.scope_combo = QtWidgets.QComboBox()
        self.scope_combo.addItem("Organization", "org")
        self.scope_combo.addItem("Project", "project")
        self.scope_combo.currentIndexChanged.connect(self._handle_scope_change)
        self.scope_combo.setStyleSheet("background-color: #1e293b; color: #f8fafc; border-radius: 8px; padding: 6px;")
        filters_layout.addLayout(_build_filter_column("Scope", self.scope_combo))

        self.project_combo = QtWidgets.QComboBox()
        self.project_combo.setEnabled(False)
        self.project_combo.setStyleSheet("background-color: #111827; color: #94a3b8; border-radius: 8px; padding: 6px;")
        filters_layout.addLayout(_build_filter_column("Project", self.project_combo))

        self.time_combo = QtWidgets.QComboBox()
        self.time_combo.setStyleSheet("background-color: #1e293b; color: #f8fafc; border-radius: 8px; padding: 6px;")
        for label, hours in self._oracle_time_options:
            self.time_combo.addItem(label, hours)
        filters_layout.addLayout(_build_filter_column("Time Window", self.time_combo))

        self.oracle_status_chip = QtWidgets.QLabel("Idle")
        self.oracle_status_chip.setAlignment(QtCore.Qt.AlignCenter)
        self.oracle_status_chip.setFixedWidth(140)
        self.oracle_status_chip.setStyleSheet(
            "border-radius: 20px; padding: 10px 12px; background-color: #334155; color: #e2e8f0; font-weight: 600;"
        )
        filters_layout.addWidget(self.oracle_status_chip, alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        layout.addWidget(filters_frame)

        self.oracle_meta_label = QtWidgets.QLabel("Awaiting first question • Scope: Organization • Window: All Activity")
        self.oracle_meta_label.setStyleSheet("color: #cbd5f5;")
        self.oracle_meta_label.setWordWrap(True)
        layout.addWidget(self.oracle_meta_label)

        self.oracle_chat_view = QtWidgets.QTextBrowser()
        self.oracle_chat_view.setOpenExternalLinks(True)
        self.oracle_chat_view.setStyleSheet(
            """
            QTextBrowser {
                background-color: #0b1120;
                border-radius: 12px;
                padding: 14px;
                color: #e2e8f0;
            }
            """
        )
        layout.addWidget(self.oracle_chat_view, 1)

        input_row = QtWidgets.QHBoxLayout()
        self.oracle_question_input = QtWidgets.QLineEdit()
        self.oracle_question_input.setPlaceholderText("e.g., Summarize what the Payments squad shipped last week.")
        self.oracle_question_input.returnPressed.connect(self._handle_oracle_question)
        self.oracle_question_input.setStyleSheet(
            "background-color: #0f172a; border: 1px solid #38bdf8; border-radius: 10px; padding: 10px; color: #f8fafc;"
        )
        input_row.addWidget(self.oracle_question_input, 1)

        self.ask_oracle_btn = QtWidgets.QPushButton("Ask Oracle")
        self.ask_oracle_btn.setMinimumHeight(40)
        self.ask_oracle_btn.setStyleSheet(
            "background-color: #38bdf8; color: #0f172a; font-weight: 700; border-radius: 12px; padding: 0 18px;"
        )
        self.ask_oracle_btn.clicked.connect(self._handle_oracle_question)
        input_row.addWidget(self.ask_oracle_btn)
        layout.addLayout(input_row)

        self._handle_scope_change()
        self._refresh_project_filters()

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

    def _handle_entry(self, entry: ActivityRecord) -> None:
        if not self.monitor:
            return
        active_id = self.monitor.get_active_session_id()
        if not active_id or entry.session_id != active_id:
            return

        entries = [e.to_ui_dict() for e in self.monitor.snapshot(active_id)]
        self.bus.buffer.emit(entries)
        self.bus.log.emit(
            f"[{entry.active_app}] {entry.task} | {entry.app_name} | deep_work={entry.is_deep_work}"
        )
        focus_text = entry.active_app or "Unknown"
        window_text = entry.window_title or "Unknown"
        if hasattr(self, "focus_chip"):
            self.focus_chip.setText(f"Active Focus: {focus_text} — {window_text}")
            if entry.focus_bounds:
                self.focus_chip.setToolTip(f"Bounds: {entry.focus_bounds}")
            else:
                self.focus_chip.setToolTip("")

    def _append_log(self, text: str) -> None:
        self.log_view.appendPlainText(text)
        self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())

    def _render_buffer(self, entries: List[dict]) -> None:
        latest = entries[-10:]
        self.buffer_table.setRowCount(len(latest))
        for row, entry in enumerate(reversed(latest)):
            self.buffer_table.setRowHeight(row, 56)
            self.buffer_table.setItem(row, 0, QtWidgets.QTableWidgetItem(entry["timestamp"]))
            self.buffer_table.setItem(row, 1, QtWidgets.QTableWidgetItem(entry["task"]))
            activity_type = entry.get("activity_type", "UNKNOWN")
            self.buffer_table.setItem(row, 2, QtWidgets.QTableWidgetItem(activity_type))

            app_label = entry.get("app_name") or entry.get("app") or "Unknown"
            app_item = QtWidgets.QTableWidgetItem(app_label)
            self.buffer_table.setItem(row, 3, app_item)

            focus_app = entry.get("active_app") or "Unknown"
            window_title = entry.get("window_title") or "Unknown"
            focus_item = QtWidgets.QTableWidgetItem(focus_app)
            focus_item.setToolTip(window_title)
            bounds = entry.get("focus_bounds")
            if bounds:
                focus_item.setToolTip(f"{window_title}\nBounds: {bounds}")
            self.buffer_table.setItem(row, 4, focus_item)

            error_label = self._format_kv("Error", entry.get("error_code"))
            doc_label = self._format_kv("Doc", entry.get("documentation_title"))
            error_text = f"{error_label}\n{doc_label}"
            doc_url = entry.get("doc_url") or entry.get("documentation_url")
            error_item = QtWidgets.QTableWidgetItem(error_text)
            if doc_url:
                error_item.setToolTip(doc_url)
            self.buffer_table.setItem(row, 5, error_item)

            privacy_state = entry.get("privacy_state", "allowed").title()
            deep_state = entry.get("deep_work_state", "deep_work")
            privacy_text = f"{privacy_state} / {deep_state}"
            privacy_item = QtWidgets.QTableWidgetItem(privacy_text)
            color = "#10b981" if entry.get("is_deep_work") else "#f87171"
            if privacy_state.lower() != "allowed":
                color = "#facc15"
            privacy_item.setForeground(QtGui.QColor(color))
            self.buffer_table.setItem(row, 6, privacy_item)

    @staticmethod
    def _format_kv(prefix: str, raw_value) -> str:
        if raw_value is None:
            return f"{prefix}: —"
        text = str(raw_value).strip()
        if not text or text in {"-", "—"}:
            return f"{prefix}: —"
        prefix_lower = f"{prefix.lower()}:"
        lowered = text.lower()
        if lowered.startswith(prefix_lower):
            text = text[len(prefix) + 1 :].strip()
        return f"{prefix}: {text or '—'}"

    def _update_status(self, state: str) -> None:
        color = "#10b981" if state == "Running" else "#4a5568"
        self.status_chip.setText(state)
        self.status_chip.setStyleSheet(
            f"border-radius: 20px; padding: 10px 18px; background-color: {color}; color: #f8fafc; font-weight: 700;"
        )

    def _log_async(self, text: str) -> None:
        self.bus.log.emit(text)

    def _restore_projects_from_disk(self) -> None:
        saved = load_saved_projects()
        restored = 0
        for entry in saved:
            project = entry.get("project_name")
            repo = entry.get("repo_path")
            if not project or not repo:
                continue
            goal = entry.get("goal") or "Resume work"
            try:
                self.monitor.create_session(project_name=project, repo_path=repo, goal=goal)
                restored += 1
            except Exception as exc:
                print(f"Failed to restore project '{project}': {exc}")
        if restored:
            self._log_async(f"Restored {restored} project(s) from disk.")
        self._refresh_project_filters()

    def _persist_projects_state(self) -> None:
        metadata = self.monitor.get_sessions_metadata()
        save_projects_state(metadata)

    def _apply_identity_to_systems(self) -> None:
        """Propagate identity settings to the monitor and other services."""
        identity = self.identity or {}
        if self.monitor:
            self.monitor.update_identity(
                user_id=identity.get("username"),
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

        scope_key = self.scope_combo.currentData() if hasattr(self, "scope_combo") else "org"
        project_name: Optional[str] = None
        if scope_key == "project":
            project_name = (self.project_combo.currentText() or "").strip()
            if not project_name or not self.project_combo.isEnabled():
                QtWidgets.QMessageBox.warning(self, "Select Project", "Choose a project before running a scoped query.")
                return

        hours = None
        if hasattr(self, "time_combo"):
            selected = self.time_combo.currentData()
            if selected and int(selected) > 0:
                hours = int(selected)

        self.ask_oracle_btn.setEnabled(False)
        self.oracle_question_input.clear()
        thread = threading.Thread(
            target=self._run_oracle_query,
            args=(question, scope_key, project_name, hours),
            daemon=True,
        )
        thread.start()

    def _run_oracle_query(
        self,
        question: str,
        scope_key: str,
        project_name: Optional[str],
        hours: Optional[int],
    ) -> None:
        self.bus.oracle_status.emit("Querying Hive Mind…")
        answer_payload = self.oracle_service.ask(
            question,
            org_id=None,
            scope=scope_key,
            project_name=project_name,
            time_window_hours=hours,
        )
        self.bus.oracle_answer.emit(answer_payload)
        self.bus.oracle_status.emit("Idle")

    def _render_oracle_answer(self, payload) -> None:
        if payload is None:
            return
        if hasattr(self, "ask_oracle_btn"):
            self.ask_oracle_btn.setEnabled(True)
        self.oracle_history.append(payload)
        self._append_oracle_card(payload)
        self._update_oracle_meta(payload)

    def _update_oracle_status(self, status: str) -> None:
        if hasattr(self, "oracle_status_chip"):
            color = "#38bdf8" if status.lower().startswith("querying") else "#334155"
            self.oracle_status_chip.setText(status)
            self.oracle_status_chip.setStyleSheet(
                f"border-radius: 20px; padding: 10px 12px; background-color: {color}; color: #e2e8f0; font-weight: 600;"
            )
        if status.lower().startswith("querying") and hasattr(self, "ask_oracle_btn"):
            self.ask_oracle_btn.setEnabled(False)
        elif status == "Idle" and hasattr(self, "ask_oracle_btn"):
            self.ask_oracle_btn.setEnabled(True)

    def _append_oracle_card(self, payload: dict) -> None:
        if not hasattr(self, "oracle_chat_view"):
            return
        question = payload.get("question") or ""
        answer = payload.get("answer") or ""
        scope_badge = self._format_scope_badge(payload)
        answer_html = self._render_oracle_markdown(answer)
        preview_html = ""
        preview = payload.get("context_preview") or []
        if preview:
            preview_lines = "".join(f"<li>{html.escape(item)}</li>" for item in preview)
            preview_html = (
                "<div style='margin-top:10px; font-size:12px; color:#94a3b8;'>Context Sample:"
                f"<ul>{preview_lines}</ul></div>"
            )

        card_html = (
            "<div style='border:1px solid rgba(56, 189, 248, 0.2); border-radius:12px; padding:12px; margin-bottom:12px;'>"
            f"<div style='font-size:12px; color:#94a3b8;'>{scope_badge}</div>"
            f"<div style='margin-top:6px;'><b>Q:</b> {html.escape(question)}</div>"
            f"<div style='margin-top:10px; line-height:1.4;'>{answer_html}</div>"
            f"{preview_html}"
            "</div>"
        )
        self.oracle_chat_view.append(card_html)
        self.oracle_chat_view.verticalScrollBar().setValue(self.oracle_chat_view.verticalScrollBar().maximum())

    def _format_scope_badge(self, payload: dict) -> str:
        scope = payload.get("scope", "org")
        project = payload.get("project_name")
        window = payload.get("time_window_hours")
        log_count = payload.get("log_count", 0)
        summary_count = payload.get("summary_count", 0)

        if scope == "project" and project:
            scope_text = f"Project • {project}"
        else:
            scope_text = "Organization • All Projects"

        window_text = f"{window}h window" if window else "All history"
        counts = f"{log_count} logs / {summary_count} summaries"
        return f"{scope_text} • {window_text} • {counts}"

    def _render_oracle_markdown(self, text: str) -> str:
        escaped = html.escape(text or "")
        return escaped.replace("\n\n", "<br><br>").replace("\n", "<br>")

    def _update_oracle_meta(self, payload: dict) -> None:
        if not hasattr(self, "oracle_meta_label"):
            return
        self.oracle_meta_label.setText(self._format_scope_badge(payload))

    def _refresh_project_filters(self) -> None:
        if not hasattr(self, "project_combo"):
            return
        projects = sorted(
            {
                meta.get("project_name", "")
                for meta in (self.monitor.get_sessions_metadata() if self.monitor else [])
                if meta.get("project_name")
            }
        )
        scope_key = self.scope_combo.currentData() if hasattr(self, "scope_combo") else "org"
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        if not projects:
            self.project_combo.addItem("No tracked projects", "")
            self.project_combo.setEnabled(False)
            self.project_combo.setStyleSheet("background-color: #111827; color: #94a3b8; border-radius: 8px; padding: 6px;")
        else:
            for project in projects:
                self.project_combo.addItem(project, project)
            enabled = scope_key == "project"
            self.project_combo.setEnabled(enabled)
            color = "#f8fafc" if enabled else "#94a3b8"
            self.project_combo.setStyleSheet(
                f"background-color: #1e293b; color: {color}; border-radius: 8px; padding: 6px;"
            )
        self.project_combo.blockSignals(False)

    def _handle_scope_change(self) -> None:
        if not hasattr(self, "scope_combo") or not hasattr(self, "project_combo"):
            return
        scope_key = self.scope_combo.currentData()
        enabled = scope_key == "project" and self.project_combo.count() > 0
        self.project_combo.setEnabled(enabled)
        color = "#f8fafc" if enabled else "#94a3b8"
        self.project_combo.setStyleSheet(
            f"background-color: #1e293b; color: {color}; border-radius: 8px; padding: 6px;"
        )
        if hasattr(self, "oracle_question_input"):
            placeholder = (
                "e.g., What did Alice work on yesterday?"
                if scope_key == "project"
                else "e.g., Summarize work on the Auth stack this week."
            )
            self.oracle_question_input.setPlaceholderText(placeholder)

    # Session management helpers -----------------------------------------

    def _open_new_session_dialog(self) -> None:
        existing_projects = sorted(
            {
                meta.get("project_name", "")
                for meta in self.monitor.get_sessions_metadata()
                if meta.get("project_name")
            }
        )
        dialog = NewSessionDialog(existing_projects, self)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return
        project_name, goal, repo_path = dialog.values()
        if not project_name or not goal or not repo_path:
            QtWidgets.QMessageBox.warning(self, "Missing Data", "Provide project, goal, and repository path.")
            return
        if not os.path.isdir(os.path.join(repo_path, ".git")):
            QtWidgets.QMessageBox.warning(self, "Invalid Repo", "Selected folder does not contain a .git directory.")
            return

        session = self.monitor.create_session(
            project_name=project_name,
            repo_path=repo_path,
            goal=goal,
        )
        self._log_async(f"Session created under project '{project_name}' with goal '{goal}'.")
        self._refresh_session_combo(select_id=session.id)
        self._persist_projects_state()
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
        self._persist_projects_state()

        new_session_id = self._current_session_id()
        if self._monitor_running and new_session_id:
            self._switch_to_session(new_session_id, clear_log=True)
        elif self._monitor_running and not new_session_id:
            self._stop_session()

    def _complete_current_session(self) -> None:
        session_id = self._current_session_id()
        if not session_id:
            return

        if (
            self._session_running
            and self.monitor
            and self.monitor.get_active_session_id() == session_id
        ):
            self._stop_session()

        self.monitor.delete_session(session_id)
        self._log_async("Session completed and removed.")
        self._refresh_session_combo()
        self._persist_projects_state()

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
            project = meta.get("project_name") or "Untitled Project"
            goal = meta.get("goal") or "Goal"
            repo_label = Path(meta["repo_path"]).name
            label = f"{project} – {goal} ({repo_label})"
            self.session_combo.addItem(label, meta["id"])

        if not metadata:
            self.session_combo.addItem("No sessions yet — click New Session", None)
            self.session_combo.setCurrentIndex(0)
            self.session_combo.blockSignals(False)
            self.delete_session_btn.setEnabled(False)
            self.complete_session_btn.setEnabled(False)
            self.start_btn.setEnabled(False)
            self._refresh_project_filters()
            self._handle_scope_change()
            return

        target_id = select_id or metadata[0]["id"]
        index = next((i for i, meta in enumerate(metadata) if meta["id"] == target_id), 0)
        self.session_combo.setCurrentIndex(index)
        self.session_combo.blockSignals(False)
        self.delete_session_btn.setEnabled(True)
        self.complete_session_btn.setEnabled(True)
        if not self._session_running:
            self.start_btn.setEnabled(True)
        self._refresh_project_filters()
        self._handle_scope_change()
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
    def __init__(self, projects: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Session")
        self.setModal(True)
        layout = QtWidgets.QFormLayout(self)

        self.project_combo = QtWidgets.QComboBox()
        self.project_combo.setEditable(True)
        self.project_combo.addItems(projects)
        layout.addRow("Project", self.project_combo)

        self.goal_input = QtWidgets.QLineEdit()
        layout.addRow("Session Goal", self.goal_input)

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
        dialog = QtWidgets.QFileDialog(self, "Select repository")
        dialog.setFileMode(QtWidgets.QFileDialog.Directory)
        dialog.setOption(QtWidgets.QFileDialog.ShowDirsOnly, True)
        dialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            selected = dialog.selectedFiles()
            if selected:
                self.repo_input.setText(selected[0])

    def values(self) -> tuple[str, str, str]:
        return (
            self.project_combo.currentText().strip(),
            self.goal_input.text().strip(),
            self.repo_input.text().strip(),
        )


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DevScope Settings")
        self.setModal(True)

        layout = QtWidgets.QFormLayout(self)
        self.username_input = QtWidgets.QLineEdit(settings.get("username", ""))
        layout.addRow("Username", self.username_input)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def values(self) -> dict:
        return {
            "username": self.username_input.text().strip(),
        }

def main():
    app = QtWidgets.QApplication(sys.argv)
    apply_stylesheet(app, theme="dark_teal.xml")
    window = DevScopeWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()


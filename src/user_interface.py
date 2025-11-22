import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout, QLineEdit
from PyQt5.QtWidgets import QDialog, QFormLayout, QCheckBox, QSpinBox, QComboBox, QShortcut, QFrame
from PyQt5.QtGui import QIcon, QFont, QPixmap, QBrush, QPalette, QColor, QTextCursor, QTextCharFormat, QKeySequence
from PyQt5.QtCore import QTime, QTimer, Qt, QProcess, QProcessEnvironment
from api_models import *
import json
import os
import site


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a2e;
                color: #ffffff;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 13px;
            }
            QComboBox, QSpinBox, QLineEdit {
                background-color: #16213e;
                color: #ffffff;
                border: 1px solid #0f3460;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
            }
            QComboBox:hover, QSpinBox:hover, QLineEdit:hover {
                border: 1px solid #4a9eff;
            }
            QCheckBox {
                color: #e0e0e0;
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #0f3460;
                border-radius: 3px;
                background-color: #16213e;
            }
            QCheckBox::indicator:checked {
                background-color: #4a9eff;
                border-color: #4a9eff;
            }
            QPushButton {
                background-color: #4a9eff;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5ab0ff;
            }
            QPushButton:pressed {
                background-color: #3a8eef;
            }
        """)

        self.layout = QFormLayout(self)
        self.layout.setSpacing(15)
        self.layout.setContentsMargins(25, 25, 25, 25)

        # model_name flag
        self.model_name_box = QComboBox()
        self.model_name_box.addItems(["gemini-2.0-flash"])
        self.layout.addRow("Model", self.model_name_box)

        # tts flag
        self.tts_checkbox = QCheckBox("Enable text-to-speech")
        self.layout.addRow("TTS", self.tts_checkbox)

        # voice flag
        self.voice_combobox = QComboBox()
        self.voice_combobox.addItems(["Adam","Arnold","Emily","Harry","Josh","Patrick"])
        self.layout.addRow("Voice", self.voice_combobox)

        # cli_mode flag
        self.cli_mode_checkbox = QCheckBox("Enable CLI mode")
        self.layout.addRow("CLI Mode", self.cli_mode_checkbox)

        # delay_time flag
        self.delay_time_spinbox = QSpinBox()
        self.delay_time_spinbox.setRange(0, 100000)
        self.layout.addRow("Delay Time", self.delay_time_spinbox)

        # initial_delay flag
        self.initial_delay_spinbox = QSpinBox()
        self.initial_delay_spinbox.setRange(0,100000)
        self.layout.addRow("Initial Delay", self.initial_delay_spinbox)

        # countdown_time flag
        self.countdown_time_spinbox = QSpinBox()
        self.countdown_time_spinbox.setRange(0, 100)
        self.layout.addRow("Countdown Time", self.countdown_time_spinbox)

        # user_name flag
        self.user_name_lineedit = QLineEdit()
        self.user_name_lineedit.setText("Procrastinator")
        self.layout.addRow("User Name", self.user_name_lineedit)

        # print_CoT flag
        self.print_CoT_checkbox = QCheckBox("Show model's chain of thought")
        self.layout.addRow("Print CoT", self.print_CoT_checkbox)

        # OK and Cancel buttons
        self.buttons_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #444444;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        self.buttons_layout.addWidget(self.ok_button)
        self.buttons_layout.addWidget(self.cancel_button)

        self.layout.addRow(self.buttons_layout)

    def get_settings(self):
        return {
            "model": self.model_name_box.currentText(),
            "tts": self.tts_checkbox.isChecked(),
            "voice": self.voice_combobox.currentText(),
            "cli_mode": self.cli_mode_checkbox.isChecked(),
            "delay_time": self.delay_time_spinbox.value(),
            "initial_delay": self.initial_delay_spinbox.value(),
            "countdown_time": self.countdown_time_spinbox.value(),
            "user_name": self.user_name_lineedit.text(),
            "print_CoT": self.print_CoT_checkbox.isChecked()
        }


class StatusIndicator(QLabel):
    """Modern status indicator with pulse animation"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self.status = "idle"  # idle, productive, procrastinating
        self.setStyleSheet("border-radius: 8px;")
        
    def set_status(self, status):
        self.status = status
        if status == "productive":
            self.setStyleSheet("background-color: #10b981; border-radius: 8px;")
        elif status == "procrastinating":
            self.setStyleSheet("background-color: #ef4444; border-radius: 8px;")
        else:
            self.setStyleSheet("background-color: #6b7280; border-radius: 8px;")


class ProcrastinationApp(QWidget):
    def __init__(self):
        super().__init__()
        self.cur_dir = os.path.dirname(__file__)
        self.initUI()
        self.start_time = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.process = None
        self.settings = load_settings()
        self.settings_dialog = SettingsDialog(self)
        self.apply_settings()

    def initUI(self):
        self.setWindowTitle('Aura - The AI Focus Partner')
        self.setGeometry(100, 100, 1000, 700)
        
        # Modern dark theme with gradient background
        self.setStyleSheet("""
            QWidget {
                background-color: #0f0f1e;
                color: #e0e0e0;
            }
        """)

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Header section with logo and title
        header_layout = QVBoxLayout()
        header_layout.setSpacing(10)
        
        # Aura branding
        aura_title = QLabel('AURA', self)
        aura_title.setFont(QFont('Segoe UI', 42, QFont.Bold))
        aura_title.setStyleSheet("color: #4a9eff; letter-spacing: 4px;")
        header_layout.addWidget(aura_title)
        
        subtitle = QLabel('The AI Focus Partner', self)
        subtitle.setFont(QFont('Segoe UI Light', 18))
        subtitle.setStyleSheet("color: #9ca3af; margin-bottom: 10px;")
        header_layout.addWidget(subtitle)
        
        # Divider line
        divider = QFrame(self)
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Sunken)
        divider.setStyleSheet("color: #1f2937; background-color: #1f2937; max-height: 1px;")
        header_layout.addWidget(divider)

        # Main content section
        content_layout = QVBoxLayout()
        content_layout.setSpacing(20)
        
        # Prompt section
        prompt_label = QLabel('What are you working on today?', self)
        prompt_label.setFont(QFont('Segoe UI', 22, QFont.Bold))
        prompt_label.setStyleSheet("color: #ffffff; margin-top: 20px;")
        content_layout.addWidget(prompt_label)
        
        hint_label = QLabel('Specify allowed and blocked activities. Aura will monitor your active window and understand context.', self)
        hint_label.setFont(QFont('Segoe UI', 12))
        hint_label.setStyleSheet("color: #6b7280; margin-bottom: 10px;")
        hint_label.setWordWrap(True)
        content_layout.addWidget(hint_label)

        self.prompt_input = QTextEdit(self)
        self.prompt_input.setFont(QFont('Inter', 14))
        self.prompt_input.setLineWrapMode(QTextEdit.WidgetWidth)
        self.prompt_input.setPlaceholderText("Example: Working on a React project. Allowed: Stack Overflow, GitHub, React docs, coding tutorials on YouTube. Not allowed: Social media, entertainment videos, games...")
        self.prompt_input.setFixedHeight(140)
        self.prompt_input.setStyleSheet("""
            QTextEdit {
                border: 2px solid #1f2937;
                border-radius: 12px;
                background-color: #16213e;
                color: #ffffff;
                padding: 18px;
                selection-background-color: #4a9eff;
                font-family: 'Inter', 'Segoe UI', sans-serif;
            }
            QTextEdit:focus {
                border: 2px solid #4a9eff;
                background-color: #1e2a47;
            }
        """)
        content_layout.addWidget(self.prompt_input)

        # Button section
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        self.start_button = QPushButton('Start Focus Session', self)
        self.start_button.clicked.connect(self.start_task)
        self.start_button.setFont(QFont('Segoe UI', 16, QFont.Bold))
        self.start_button.setFixedHeight(56)
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.start_button.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 12px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4a9eff, stop:1 #5ab0ff);
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 0px 30px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5ab0ff, stop:1 #6ac0ff);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3a8eef, stop:1 #4a9eff);
            }
        """)
        
        self.settings_button = QPushButton('⚙ Settings', self)
        self.settings_button.clicked.connect(self.open_settings)
        self.settings_button.setFont(QFont('Segoe UI', 14))
        self.settings_button.setFixedHeight(56)
        self.settings_button.setFixedWidth(140)
        self.settings_button.setCursor(Qt.PointingHandCursor)
        self.settings_button.setStyleSheet("""
            QPushButton {
                border: 2px solid #374151;
                border-radius: 12px;
                background-color: #1f2937;
                color: #e0e0e0;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #374151;
                border: 2px solid #4a9eff;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #111827;
            }
        """)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.settings_button)
        button_layout.addStretch()

        # Create a shortcut for Ctrl+Enter
        shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        shortcut.activated.connect(self.start_button.click)
        
        settings_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        settings_shortcut.activated.connect(self.settings_button.click)
        
        # Wrap initial screen content in a widget for easy hiding/showing
        self.initial_widget = QWidget()
        initial_layout = QVBoxLayout()
        initial_layout.setContentsMargins(40, 40, 40, 40)
        initial_layout.setSpacing(25)
        initial_layout.addLayout(header_layout)
        initial_layout.addLayout(content_layout)
        initial_layout.addLayout(button_layout)
        initial_layout.addStretch()
        self.initial_widget.setLayout(initial_layout)
        
        # Running screen elements (hidden initially)
        running_header = QHBoxLayout()
        
        self.running_label = QLabel('Focus Session', self)
        self.running_label.setFont(QFont('Segoe UI', 24, QFont.Bold))
        self.running_label.setStyleSheet("color: #ffffff; background: transparent;")
        
        self.status_indicator = StatusIndicator(self)
        
        self.task_label = QLabel('', self)
        self.task_label.setFont(QFont('Segoe UI', 14))
        self.task_label.setStyleSheet("color: #9ca3af; background: transparent;")
        self.task_label.setWordWrap(True)
        
        running_header.addWidget(self.running_label)
        running_header.addWidget(self.status_indicator)
        running_header.addSpacing(15)
        running_header.addStretch()
        
        self.timer_label = QLabel('⏱ 00:00:00', self)
        self.timer_label.setFont(QFont('Segoe UI Semibold', 18))
        self.timer_label.setStyleSheet("color: #4a9eff; background: transparent;")
        
        self.output_display = QTextEdit(self)
        self.output_display.setReadOnly(True)
        self.output_display.setFont(QFont('Consolas', 11))
        self.output_display.setStyleSheet("""
            QTextEdit {
                border: 2px solid #1f2937;
                border-radius: 12px;
                background-color: #0a0a15;
                color: #d1d5db;
                padding: 20px;
                selection-background-color: #4a9eff;
                font-family: 'Consolas', 'Courier New', monospace;
            }
        """)
        
        self.stop_button = QPushButton('⏹ Stop Session', self)
        self.stop_button.clicked.connect(self.stop_task)
        self.stop_button.setFont(QFont('Segoe UI', 14, QFont.Bold))
        self.stop_button.setFixedHeight(50)
        self.stop_button.setCursor(Qt.PointingHandCursor)
        self.stop_button.setStyleSheet("""
            QPushButton {
                border: 2px solid #ef4444;
                border-radius: 12px;
                background-color: rgba(239, 68, 68, 0.1);
                color: #ef4444;
                padding: 12px 24px;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.2);
                border: 2px solid #f87171;
            }
            QPushButton:pressed {
                background-color: rgba(239, 68, 68, 0.15);
            }
        """)
        
        self.chat_button = QPushButton('💬 Change Task', self)
        self.chat_button.clicked.connect(self.show_chat)
        self.chat_button.setFont(QFont('Segoe UI', 14))
        self.chat_button.setFixedHeight(50)
        self.chat_button.setCursor(Qt.PointingHandCursor)
        self.chat_button.setStyleSheet("""
            QPushButton {
                border: 2px solid #374151;
                border-radius: 12px;
                background-color: #1f2937;
                color: #e0e0e0;
                padding: 12px 24px;
            }
            QPushButton:hover {
                background-color: #374151;
                border: 2px solid #4a9eff;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #111827;
            }
        """)
        
        self.back_button = QPushButton('← Back to Monitor', self)
        self.back_button.clicked.connect(self.show_stdout)
        self.back_button.setFont(QFont('Segoe UI', 12))
        self.back_button.setCursor(Qt.PointingHandCursor)
        self.back_button.setStyleSheet("""
            QPushButton {
                border: 1px solid #374151;
                border-radius: 8px;
                background-color: #1f2937;
                color: #9ca3af;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #374151;
                color: #ffffff;
            }
        """)
        
        # Chat elements (hidden initially)
        self.chat_area = QTextEdit(self)
        self.chat_area.setReadOnly(True)
        self.chat_area.setFont(QFont('Segoe UI', 13))
        self.chat_area.setStyleSheet("""
            QTextEdit {
                background-color: #0a0a15;
                color: #ffffff;
                border: 2px solid #1f2937;
                border-radius: 12px;
                padding: 20px;
                selection-background-color: #4a9eff;
            }
        """)
        
        self.input_area = QLineEdit(self)
        self.input_area.setFont(QFont('Segoe UI', 14))
        self.input_area.setPlaceholderText("Type your new task...")
        self.input_area.setStyleSheet("""
            QLineEdit {
                background-color: #16213e;
                color: #ffffff;
                border: 2px solid #1f2937;
                border-radius: 10px;
                padding: 14px 18px;
                selection-background-color: #4a9eff;
                font-family: 'Segoe UI', sans-serif;
            }
            QLineEdit:focus {
                border: 2px solid #4a9eff;
                background-color: #1e2a47;
            }
        """)
        self.input_area.returnPressed.connect(self.send_message)
        
        self.send_button = QPushButton('Send', self)
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setFont(QFont('Segoe UI', 14, QFont.Bold))
        self.send_button.setFixedHeight(50)
        self.send_button.setFixedWidth(100)
        self.send_button.setCursor(Qt.PointingHandCursor)
        self.send_button.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 10px;
                background-color: #4a9eff;
                color: white;
            }
            QPushButton:hover {
                background-color: #5ab0ff;
            }
            QPushButton:pressed {
                background-color: #3a8eef;
            }
        """)
        
        # Running screen layout
        self.running_layout = QVBoxLayout()
        self.running_layout.setContentsMargins(40, 40, 40, 40)
        self.running_layout.setSpacing(20)
        self.running_layout.addLayout(running_header)
        self.running_layout.addWidget(self.task_label)
        self.running_layout.addWidget(self.timer_label)
        self.running_layout.addWidget(self.output_display)
        
        button_row = QHBoxLayout()
        button_row.addWidget(self.stop_button)
        button_row.addWidget(self.chat_button)
        button_row.addStretch()
        self.running_layout.addLayout(button_row)
        
        chat_input_layout = QHBoxLayout()
        chat_input_layout.addWidget(self.input_area)
        chat_input_layout.addWidget(self.send_button)
        
        self.chat_layout = QVBoxLayout()
        self.chat_layout.setContentsMargins(40, 40, 40, 40)
        self.chat_layout.setSpacing(15)
        self.chat_layout.addWidget(self.back_button)
        self.chat_layout.addWidget(self.chat_area)
        self.chat_layout.addLayout(chat_input_layout)
        
        self.chat_widget = QWidget()
        self.chat_widget.setLayout(self.chat_layout)
        
        self.running_widget = QWidget()
        self.running_widget.setLayout(self.running_layout)
        
        self.layout.addWidget(self.initial_widget)
        self.layout.addWidget(self.running_widget)
        self.layout.addWidget(self.chat_widget)
        
        self.running_widget.hide()
        self.chat_widget.hide()
        
        self.setLayout(self.layout)
        self.show()  # Make sure window is shown

    def start_task(self, task_description=None):
        if not task_description:
            task_description = self.prompt_input.toPlainText()
        if task_description:
            if self.process:
                self.process.terminate()
                self.process.waitForFinished()

            self.task_label.setText(task_description)
            if self.status_indicator:
                self.status_indicator.set_status("idle")

            self.process = QProcess(self)
            arguments = ["-u", os.path.dirname(__file__)+"/main.py"]

            if self.settings["tts"]:
                arguments.append("--tts")
            if self.settings["cli_mode"]:
                arguments.append("--cli_mode")
            if self.settings["print_CoT"]:
                arguments.append("--print_CoT")
            arguments.extend([
                "--model", self.settings["model"],
                "--voice", self.settings["voice"],
                "--delay_time", str(self.settings["delay_time"]),
                "--initial_delay", str(self.settings["initial_delay"]),
                "--countdown_time", str(self.settings["countdown_time"]),
                "--user_name", self.settings["user_name"]
            ])

            # Use the same Python interpreter that's running this GUI
            # This ensures we use the same environment (conda base, venv, etc.)
            import sys
            python_executable = sys.executable
            
            # Try to use virtual environment Python first (if it exists)
            venv_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "focusenv", "bin")
            venv_candidates = [
                os.path.join(venv_dir, "python3"),
                os.path.join(venv_dir, "python"),
            ]
            for venv_python in venv_candidates:
                if os.path.exists(venv_python):
                    self.process.setProgram(venv_python)
                    break
            else:
                # Use the same Python that's running this script
                self.process.setProgram(python_executable)
            
            # Explicitly set the environment to ensure conda environment is inherited
            env = QProcessEnvironment.systemEnvironment()
            # Copy all current environment variables (including conda paths)
            for key, value in os.environ.items():
                env.insert(key, value)
            
            # Dynamically find and set PYTHONPATH to ensure all packages are found
            site_packages_paths = site.getsitepackages()
            
            # Add the user site-packages directory as well
            if site.getusersitepackages() not in site_packages_paths:
                site_packages_paths.append(site.getusersitepackages())

            # Construct the PYTHONPATH string
            python_path = os.pathsep.join(site_packages_paths)

            # Get current PYTHONPATH and append new paths
            current_pythonpath = env.value("PYTHONPATH", "")
            if current_pythonpath:
                python_path = f"{python_path}{os.pathsep}{current_pythonpath}"

            env.insert("PYTHONPATH", python_path)
            self.process.setProcessEnvironment(env)
            
            self.process.setArguments(arguments)
            self.process.setProcessChannelMode(QProcess.MergedChannels)
            self.process.readyReadStandardOutput.connect(self.handle_stdout)
            self.process.start()
            self.process.write(task_description.encode() + b'\n')
            self.process.closeWriteChannel()

            if self.start_time is None:
                self.start_time = QTime.currentTime()
                self.timer.start(1000)  # Update every second

            # Switch to running screen
            self.initial_widget.hide()
            self.running_widget.show()

    def handle_stdout(self):
        output = self.process.readAllStandardOutput().data().decode()
        elapsed_time = QTime(0, 0).addSecs(self.start_time.secsTo(QTime.currentTime())).toString('hh:mm:ss')
        timestamped_output = f"{elapsed_time} - {output}"

        cursor = self.output_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        # Apply conditional coloring and status updates
        format = QTextCharFormat()
        
        output_lower = output.lower()
        if "procrastinating" in output_lower:
            format.setForeground(QColor("#ef4444"))
            if self.status_indicator:
                self.status_indicator.set_status("procrastinating")
        elif "productive" in output_lower:
            format.setForeground(QColor("#10b981"))
            if self.status_indicator:
                self.status_indicator.set_status("productive")
        else:
            format.setForeground(QColor("#6b7280"))
        
        cursor.insertText(timestamped_output, format)
        self.output_display.setTextCursor(cursor)
    
    def update_timer(self):
        if self.start_time:
            elapsed_time = QTime(0, 0).secsTo(QTime.currentTime()) - QTime(0, 0).secsTo(self.start_time)
            formatted_time = QTime(0, 0).addSecs(elapsed_time).toString('hh:mm:ss')
            self.timer_label.setText(f'⏱ {formatted_time}')
        
    def stop_task(self):
        self.timer.stop()
        if self.process:
            self.process.terminate()
            self.process.waitForFinished()
        print("Stopping task")
        self.close()

    def resizeEvent(self, event):
        # Remove background image for cleaner look
        pass

    def open_settings(self):
        if self.settings_dialog.exec_():
            self.settings = self.settings_dialog.get_settings()
            save_settings(self.settings)
            print("Settings updated:", self.settings)

    def show_chat(self):
        self.running_widget.hide()
        self.chat_widget.show()
        
        self.chat_area.clear()
        self.chat_area.append("<b style='color: #4a9eff;'>Aura:</b> What would you like to work on?")
        
    def show_stdout(self):
        self.chat_widget.hide()
        self.running_widget.show()
        
    def send_message(self):
        user_message = self.input_area.text()
        if user_message:
            self.chat_area.append(f"<b style='color: #ffffff;'>You:</b> {user_message}")
            self.input_area.clear()
            model = create_model(self.settings["model"])
            system_prompt = "You are a charismatic productivity assistant chatbot. You give short encouraging responses."
            user_prompt = f"The User just updated their task specification. It is pasted below. Please give a brief response telling them that their task has been updated and a little bit of personalized ecouragement. But no matter what, don't sound cliche.\n\n{user_message}"            
            ai_message = model.call_model(user_prompt, system_prompt=system_prompt)
            self.chat_area.append(f"<b style='color: #4a9eff;'>Aura:</b> {ai_message}")
            # Restart the backend with the user's message as stdin
            self.start_task(user_message)

    def apply_settings(self):
        self.settings_dialog.model_name_box.setCurrentText(self.settings["model"])
        self.settings_dialog.tts_checkbox.setChecked(self.settings["tts"])
        self.settings_dialog.voice_combobox.setCurrentText(self.settings["voice"])
        self.settings_dialog.cli_mode_checkbox.setChecked(self.settings["cli_mode"])
        self.settings_dialog.delay_time_spinbox.setValue(self.settings["delay_time"])
        self.settings_dialog.initial_delay_spinbox.setValue(self.settings["initial_delay"])
        self.settings_dialog.countdown_time_spinbox.setValue(self.settings["countdown_time"])
        self.settings_dialog.user_name_lineedit.setText(self.settings["user_name"])
        self.settings_dialog.print_CoT_checkbox.setChecked(self.settings["print_CoT"])


def load_settings():
    settings_file = os.path.dirname(os.path.dirname(__file__)) + "/settings.json"
    if os.path.exists(settings_file):
        with open(settings_file, "r") as file:
            return json.load(file)
    else:
        return {
            "model": "gemini-2.0-flash",
            "tts": False,
            "voice": "Patrick",
            "cli_mode": False,
            "delay_time": 0,
            "initial_delay": 0,
            "countdown_time": 15,
            "user_name": "Procrastinator",
            "print_CoT": False
        }

def save_settings(settings):
    settings_file = os.path.dirname(os.path.dirname(__file__)) + "/settings.json"
    with open(settings_file, "w") as file:
        json.dump(settings, file)



if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(os.path.dirname(os.path.dirname(__file__))+'/assets/icon_rounded.png'))
    app.setApplicationName('Aura - The AI Focus Partner')
    ex = ProcrastinationApp()
    sys.exit(app.exec_())

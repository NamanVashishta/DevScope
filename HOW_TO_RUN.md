# How to Run DevScope (macOS Build)

DevScope is a macOS-native recorder + agentic layer for engineering teams. This guide covers the manual steps to launch the monitor, triggers, and UI.

---

## 1. Open the project

```bash
cd /path/to/Transparent-Focus-Agent
```

## 2. Activate the virtualenv

```bash
python3 -m venv focusenv
source focusenv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

Already have `focusenv/`? Just `source focusenv/bin/activate`.

## 3. Export credentials

```bash
export GEMINI_API_KEY="AIza..."
export SLACK_BOT_TOKEN="xoxb-..."
# optional: export ELEVEN_LABS_API_KEY="eleven-..."
```

Add them to `~/.zshrc` for persistence.

## 4. Launch the UI

```bash
python3 src/ui.py
```

- Click **Select Project Folder** → choose the repo to watch.
- Press **Start Session** to spin up the monitor + triggers.
- Watch the status log for buffer entries, Slack replies, and git context dumps.

---

## Command-line reference

Single-line launch:
```bash
cd /path/to/Transparent-Focus-Agent && \
source focusenv/bin/activate && \
export GEMINI_API_KEY="..." && \
export SLACK_BOT_TOKEN="..." && \
python3 src/ui.py
```

---

## Settings you’ll see in the UI

- **Capture cadence:** Seconds between screenshots (default 10).
- **Deep work threshold:** Minimum consecutive “is_deep_work” entries before shielding Slack.
- **Auto-answer toggle:** Enable/disable Slack automation.
- **Privacy list:** Path to YAML file (coming soon) that blocks specific apps/URLs.

---

## Troubleshooting

### GUI never appears
1. Confirm `PyQt5` and `qt-material` are installed in the virtualenv (`pip show PyQt5`).
2. Run `python3 -m PyQt5.QtWidgets` to verify Qt works.
3. Check macOS Gatekeeper: System Settings → Privacy & Security → allow Python to record the screen.

### Screen capture errors
- Make sure Terminal (or your IDE) has Screen Recording permission.
- Reboot after granting permission if frames remain blank.
- Verify `mss` can access multiple displays; disable Stage Manager temporarily if captures are offset.

### Gemini/Slack failures
- Ensure `GEMINI_API_KEY` is valid and not rate-limited. Try `curl https://generativelanguage.googleapis.com/v1beta/models`.
- For Slack, double-check the bot token scopes: `im:history`, `chat:write`, `users:read`.
- Restart the UI after updating environment variables; the monitor inherits them only at launch.

---

## Shutdown

- Click **Stop Session** in the UI to gracefully halt all threads.
- Remove `temp_disk/` to clear cached frames (they’re auto-purged every 30 min regardless).
- `deactivate` to exit the virtualenv.


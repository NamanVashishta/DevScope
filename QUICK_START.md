# DevScope Quick Start (macOS)

DevScope currently targets macOS Sequoia/Sonoma. Follow these steps to go from clone → running the PyQt control panel.

## 1. Install prerequisites

- Python 3.10+ (Homebrew: `brew install python@3.11`)
- Xcode Command Line Tools (`xcode-select --install`)
- FFmpeg (optional, legacy TTS): `brew install ffmpeg`

## 2. Clone and bootstrap

```bash
git clone git@github.com:NamanVashishta/DevScope.git
cd DevScope
python3 -m venv focusenv
source focusenv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Configure API tokens

```bash
export GEMINI_API_KEY="AIza..."
# optional: export ELEVEN_LABS_API_KEY="eleven-..."
```

Add the exports to `~/.zshrc` if you want them to persist.

## 4. Grant permissions

1. Launch once to trigger the macOS Screen Recording prompt, or open System Settings → Privacy & Security → Screen Recording → enable for Terminal/Python.
2. If you plan to capture multiple displays, allow “Record entire screen”.

## 5. Run the control panel

```bash
python3 src/ui.py
```

In the UI:
- Click “Select Project Folder” and choose the repo you want DevScope to shadow.
- Press “Start Session”. The monitor + triggers spin up, and the log panel will stream buffer summaries and events.

## 6. Demo script

1. Open VS Code and a browser with docs. DevScope begins capturing every 10 s.
2. Make a git commit. Check the generated Markdown context report under `<repo>/.devscope/context-<commit>.md` for the expanded timeline + AI summary.

## Troubleshooting

- **No frames in `temp_disk/`:** Re-run after granting Screen Recording; check Console for `CGWindowList` permission errors.
- **Gemini errors:** Verify `GEMINI_API_KEY` and network connectivity. Try `pip install google-generativeai==0.5.*`.
- **PyQt crash:** Ensure `qt-material` is installed (`pip install qt-material`) and macOS is not blocking unsigned apps.

Still stuck? See `HOW_TO_RUN.md` or run `python3 scripts/devscope_demo.py` (coming soon) for a mocked walkthrough.


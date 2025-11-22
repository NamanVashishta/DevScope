# Complete Prerequisites List for Aura (macOS)

## 🎯 What YOU Need to Install Manually

### 1. **Python 3.8 or Higher** ✅ REQUIRED
- Check your version: `python3 --version`
- Install via Homebrew if needed: `brew install python3`
- macOS 14+ already ships with Python 3.9+, but Homebrew gives you the newest bugfixes.

### 2. **API Keys** ✅ REQUIRED
- `GEMINI_API_KEY` (Gemini 2.0 Flash): https://aistudio.google.com/app/apikey
- `ELEVEN_LABS_API_KEY` (optional for text-to-speech nudges)

---

## 📦 What Gets Installed Automatically (via `./run.sh`)

You do **not** need to install these by hand—the launcher script handles everything:

- **GUI**: PyQt5, Qt5 libraries, SIP bindings.
- **AI Client**: `google-generativeai` (Gemini SDK).
- **Imaging**: `mss`, `pillow`, `opencv-python`.
- **Audio/TTS**: `sounddevice`, `soundfile`, `pydub`, `requests`.
- **Utilities**: `PyYAML`, `psutil`, plus 100+ transitive packages.

---

## ✅ Your Current Status (Example)

- ✅ Python 3.12.7 installed
- ✅ Gemini API key exported
- ⏳ Dependencies will auto-install when you execute `./run.sh`

---

## 🚀 What Happens When You Run `./run.sh`

1. Creates `focusenv/` (Python virtual environment).
2. Activates it and installs everything from `requirements.txt`.
3. Launches `src/user_interface.py` via PyQt5.
4. When you quit the GUI, the script deactivates the venv.

> You never have to pip-install PyQt5 or other heavy deps manually.

---

## 💡 TL;DR

You need:
1. ✅ Python 3.8+ (preferably via Homebrew)
2. ✅ At least one API key (Gemini recommended)

Everything else is scripted.

---

## 🎯 Ready to Run?

```bash
cd /path/to/Transparent-Focus-Agent
export GEMINI_API_KEY="AIza..."   # add ELEVEN_LABS_API_KEY if you want TTS
chmod +x run.sh                   # first time only
./run.sh
```

Sit tight while the environment provisions, then start your focus session—everything is tailored for macOS.


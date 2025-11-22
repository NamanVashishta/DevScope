# How to Run Aura (macOS Build)

## 🚀 Quick Start (3 Steps)

### 1. Open Terminal in the project directory
```bash
cd /path/to/Transparent-Focus-Agent
```

### 2. Export your Gemini API key
```bash
export GEMINI_API_KEY="AIza..."
```
Optional: add `ELEVEN_LABS_API_KEY` if you want text-to-speech heckling.

### 3. Launch Aura
```bash
chmod +x run.sh   # first time only
./run.sh
```
The script builds/activates `focusenv`, installs dependencies, and starts the PyQt GUI.

---

## 🎯 Inside the App

1. Describe your goal plus allowed/blocked behaviors, e.g.
   ```
   Working on iOS onboarding flow.
   Allowed: Xcode, Figma, Slack (project channels).
   Not allowed: Instagram, YouTube (non-work), news.
   ```
2. Press `Start` (or `Cmd+Enter`).
3. Aura grabs the active window every few seconds and nudges you if you drift.

---

## 📝 One-Line Command (macOS)

```bash
cd /path/to/Transparent-Focus-Agent && \
export GEMINI_API_KEY="AIza..." && \
./run.sh
```

Want a persistent env? Append the `export` lines to `~/.zshrc` and skip that step next time.

---

## ⚙️ Settings Panel

- **Model**: Fixed to `gemini-2.0-flash` in this build.
- **Delay Time**: Seconds between screenshots (0 = continuous).
- **Countdown**: Seconds to comply once caught (default 15).
- **TTS**: Enable Eleven Labs voices when `ELEVEN_LABS_API_KEY` is set.

---

## 🔄 If the GUI Doesn't Appear

1. Ensure the script created `focusenv/bin/python3`. If not, delete `focusenv/` and re-run `./run.sh`.
2. Manually install deps:
   ```bash
   python3 -m venv focusenv
   source focusenv/bin/activate
   pip install --upgrade pip setuptools wheel
   pip install -r requirements.txt
   python3 src/user_interface.py
   ```
3. Confirm macOS Screen Recording permission is enabled for Terminal/Python.

---

## 💡 Tips

- Gemini 2.0 Flash stays free if you keep `delay_time` in the 5–10 second range.
- Close Aura via the Stop button or by quitting the window; the virtualenv deactivates automatically.

---

## 🎉 That's It

On macOS, running `./run.sh` is all you need—no legacy artifacts, no extra scripts. Stay focused! 🚀


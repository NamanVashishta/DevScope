# Aura - The AI Focus Partner - Quick Start Guide (macOS)

Aura now targets macOS only. Follow these steps to go from clone → running GUI in a couple of minutes.

## 🚀 Fastest Way to Get Started on macOS

1. **Install Python 3.8+** (if not already installed)
   - Check: `python3 --version`
   - Install via Homebrew: `brew install python3` (or download from [python.org](https://www.python.org/downloads/))

2. **Clone and enter the project**
   ```bash
   git clone <your-repo-url>
   cd Transparent-Focus-Agent
   ```

3. **Run the launcher script**
   ```bash
   chmod +x run.sh    # one-time, if needed
   ./run.sh
   ```
   The script will create/activate `focusenv`, install dependencies, and launch the PyQt GUI.

4. **Grant Screen Recording permission**
   - First launch triggers the macOS prompt; approve it.
   - Or manually: System Settings → Privacy & Security → Screen Recording → enable for Terminal (or your IDE).
   - Restart Aura after toggling permissions.

5. **Set your API keys**
   ```bash
   export GEMINI_API_KEY="AIza..."
   export ELEVEN_LABS_API_KEY="eleven-..."   # optional, for TTS
   ```
   Make them persistent by appending to `~/.zshrc` or `~/.bash_profile`, then `source` the file.

6. **Start a session**
   - Enter goal + allowed/blocked behaviors.
   - Click `Start` (or press `Cmd+Enter`).
   - Aura captures the active window every few seconds and intervenes if you drift.

## 💡 Tips

- **Free tier**: Gemini 2.0 Flash is fast and $0 (with a generous monthly cap).
- **Delay tuning**: 5–10 s `delay_time` balances accuracy vs. cost; 0 s is full streaming.
- **TTS reminders**: Enable Eleven Labs voices for spoken nudges if you exported `ELEVEN_LABS_API_KEY`.

## ⚙️ Recommended Settings

- **Default**: `model_name=gemini-2.0-flash`, `delay_time=5`, `countdown_time=15`.
- **Maximum accuracy**: `model_name=gemini-2.0-flash`, `delay_time=0`, `print_CoT=true`.

## 📝 Session Prompt Examples

**Coding**
```
I'm implementing OAuth in my Flask backend.
Allowed: VS Code, Stack Overflow, GitHub docs, Postman.
Not allowed: Twitter, YouTube (unless coding tutorial), news.
```

**Writing**
```
I'm drafting the Related Work section for my HCI paper.
Allowed: ACM DL, Zotero, PDF readers, Google Scholar.
Not allowed: entertainment sites, messaging apps, online shopping.
```

**Studying**
```
I'm revising for my calculus midterm.
Allowed: Khan Academy, Desmos, lecture slides.
Not allowed: games, social media, YouTube (except study channels).
```

## 🆘 Problems?

- Consult `MAC_SETUP.md` for detailed troubleshooting (permissions, PyQt install, Gemini setup).
- Still stuck? Run `python3 -m pip install --upgrade pip setuptools wheel`, re-run `./run.sh`, and re-check Screen Recording toggles.


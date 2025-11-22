# 👁️ DevScope: The Visual Cortex for Engineering Teams

![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![AI](https://img.shields.io/badge/Powered%20by-Gemini%202.0%20Flash-orange)
![Status](https://img.shields.io/badge/Hackathon-Cerebral%20Valley-purple)

> **"Software collaboration is broken. We interrupt engineers like routers—asking 'What are you working on?' or 'Where are the API keys?' Every ping kills flow."**

**DevScope** runs locally, watches what you see, and automates the context engineers usually type into countless messages. It captures visual history, protects deep-work time, answers teammates, and attaches rich context to commits.

---

## ⚡ The Pitch

DevScope keeps a **Visual Memory** (Hybrid Ring Buffer) of the workspace so makers can stay in flow while the agent keeps collaborators informed.

### 🚀 Key Features

| Feature | Description |
| :--- | :--- |
| 🛡️ **Protects Flow** | Detects *Deep Work* and shields Slack unless the agent can answer on your behalf. |
| 🧠 **Visual RAG** | Searches the visual buffer to resolve teammate questions automatically (“.env was open 2 min ago; here’s the snippet.”). |
| 🤝 **Automated Handoffs** | On `git commit`, DevScope freezes the last ~30 min of activity and emits a Markdown context report. |

---

## 🏗️ Architecture

DevScope’s **Hybrid Ring Buffer** samples the screen every 10 s, labels frames with Gemini 2.0 Flash, and stores structured metadata while purging old images.

1. **Capture:** Quartz/MSS → `temp_disk/frame_<timestamp>.png`
2. **Process:** Gemini labels each frame (`task`, `app`, `technical_context`, `is_deep_work`)
3. **Purge:** `collections.deque(maxlen=180)` keeps ~30 minutes; rolling off deletes the PNG.

### Metadata Schema

```json
{
  "timestamp": "2025-11-22T18:14:52Z",
  "task": "Debugging",
  "app": "VS Code",
  "technical_context": "Error 500 in payments.py",
  "is_deep_work": true,
  "image_path": "temp_disk/frame_492.png"
}
```

### Component Map

| File | Role |
|------|------|
| `src/monitor.py` | Visual Engine: capture → Gemini labeling → ring buffer + privacy guard. |
| `src/triggers.py` | Agentic layer: Git watcher dumps context reports; Slack watcher auto-responds using buffer history. |
| `src/ui.py` | PyQt5 + `qt-material` dashboard for selecting repos, starting sessions, and watching live logs. |
| `src/utils.py` | macOS Quartz pipeline, temp-disk helpers, privacy filters. |

---

## 🔒 Privacy & Ethics (The Defense)

- **Is this spyware?** No. The buffer lives locally and purges every 30 min. Data only leaves the device when you explicitly share it (Slack reply or commit report). DevScope defends the maker, not the manager.
- **What about private apps?** Set `DEVSCOPE_PRIVACY_APPS="Safari,Notes,1Password"` (etc.). Blocklisted apps never get captured—vision runs locally before the frame is stored.
- **How do you link context to commits?** A watchdog monitors `.git/logs/HEAD`. On commit, the buffer freezes and becomes a Markdown “Context Report” attached under `.devscope/`.

---

## 🛠️ Setup & Installation

### Prerequisites

- macOS Sequoia/Sonoma with Screen Recording permission  
- Python 3.10+  
- `GEMINI_API_KEY` (Gemini 2.0 Flash)  
- `SLACK_BOT_TOKEN` (DM scopes for auto replies)  
- Optional: `ELEVEN_LABS_API_KEY` for legacy TTS  

### Quick Start

```bash
# 1. Clone
git clone https://github.com/yourusername/devscope.git
cd devscope

# 2. Install
python3 -m venv focusenv && source focusenv/bin/activate
pip install -r requirements.txt

# 3. Configure
export GEMINI_API_KEY="AIza..."
export SLACK_BOT_TOKEN="xoxb-..."

# 4. Run
python3 src/ui.py
```

Grant Screen Recording in **System Settings → Privacy & Security → Screen Recording** for Terminal/Python.

---

## 🎥 Demo Flow

1. Launch the UI, pick a repo, press **Start Session**.  
2. Watch the “Visual Ring Buffer” table populate with Gemini labels (“Debugging FastAPI”).  
3. Send a Slack DM from another account: “Where are the API keys?”  
4. DevScope intercepts, inspects the buffer, and replies automatically if context exists.  
5. Make a git commit—check `.devscope/context-<hash>.md` for the auto-generated handoff summary.

---

## 🗺️ Roadmap

- [ ] Buffer analytics (flow vs fragmentation heatmaps)  
- [ ] Privacy-first OCR redaction prior to Gemini upload  
- [ ] Windows/Linux capture via Win32 & X11 pipelines  
- [ ] Packaging (PyInstaller/dmg) for one-click installs  

---

## 📄 License

DevScope is released under the **MIT License** (see `LICENSE`).  
If you need the text inline:

```
MIT License

Copyright (c) 2025 Naman Vashishta (Team DevScope)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

**DevScope shifts collaboration from synchronous interruption to asynchronous intelligence.**

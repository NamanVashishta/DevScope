# 👁️ DevScope: The Visual Cortex for Engineering Teams

[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![AI](https://img.shields.io/badge/Powered%20by-Gemini%202.0%20Flash-orange)
![Status](https://img.shields.io/badge/Hackathon-Cerebral%20Valley-purple)

> **"Software collaboration is broken. We interrupt engineers like routers—asking 'What are you working on?' or 'Where are the API keys?' Every ping kills flow."**

**Track:** Statement Three – Collaborative Code Generation Tooling  
**Tagline:** *The Visual Cortex for Engineering Teams.*

**DevScope** is an Organization-Wide Intelligence Platform. It runs silently on every engineer’s Mac, uses Gemini 2.0 Flash to understand what’s happening on-screen, and turns that context into a searchable Hive Mind backed by MongoDB Atlas.

---

## 🚨 Problem — The Black Box of Engineering

- **Bus Factor:** When a developer leaves, history leaves with them. Commits show *what* changed, never *how* we got there.  
- **Interruption Tax:** Getting context means DM pings (“Hey, how does the Auth API work?”). Every sync interruption kills flow.  
- **Humans as Routers:** Engineers burn cycles ferrying tribal knowledge instead of building. Context lives in heads, tickets, and transient chats.

We need shared memory without forcing humans to write docs mid-sprint.

---

## 💡 Solution — DevScope Hive Mind

| Capability | Description |
| --- | --- |
| **Capture Context** | Dual-Context Vision Engine watches the full desktop plus the active window focus every 10 s, labeling tasks like “Debugging Stripe Error 409.” |
| **Centralize Intelligence** | Only “Deep Work” frames are distilled into textual metadata and synced to MongoDB Atlas, creating an org-wide memory graph. |
| **Automate Collaboration** | Teammates query the Oracle UI (“Who touched the Auth API last week?”) and get instant answers without interrupting anyone. |

DevScope converts each maker’s flow into a self-updating wiki so knowledge survives departures, vacations, and timezone gaps.

---

## 🧬 Technology Pillars (Secret Sauce)

### 1. Dual-Context Vision Engine (`src/monitor.py`)
- **Panoramic Input:** `mss` stitches every monitor into one frame for peripheral awareness (docs, dashboards, second-screen tabs).  
- **Foveal Focus:** AppKit/Quartz pulls the precise app + window title under the cursor/keyboard.  
- **Gemini 2.0 Flash Prompting:** System prompt highlights focus metadata so Deep Work detection weights the active app while still learning from background context.  
- **Ring Buffer:** Per-session deque keeps ~30 minutes of labeled activity; rolling frames delete PNGs to keep storage bounded.

### 2. MongoDB Atlas Hive Mind (`src/db.py`)
- **Deep Work Filter:** Metadata is uploaded only if the frame is aligned with the stated goal. Social media, banking, or idle states never leave the laptop.  
- **Flexible Schema:** Each document stores timestamp, project, technical context, and alignment score—perfect for Visual RAG without schema migrations.  
- **Org-Level Tagging:** Every record carries `org_id`, `user_id`, and `project_name`, so queries can scope to a squad or span the entire company.

### 3. Privacy Firewall
- **Local Privacy Classifier:** `DEVSCOPE_PRIVACY_APPS` opt-out list halts capture before the frame is saved.  
- **No Screenshots in the Cloud:** Only the JSON insights travel to Atlas; raw images remain local and expire with the ring buffer.  
- **Maker-First Controls:** We verify *Deep Work* before we verify *Upload*.

### 4. Collaborative Surfaces
- **Mission Control UI (`src/ui.py`):** PyQt dashboard for multi-session management, live logs, and git trigger status.  
- **Oracle Tab (`src/oracle.py`):** Query-specific project or org-wide scope; Gemini summarizes the retrieved logs into natural language answers.  
- **Ghost Team Seeder (`scripts/ghost_team.py`):** CLI utility that injects believable Alice/Bob activity for demos or local testing.

---

## 🏗️ Architecture at a Glance

1. **Capture:** Quartz/AppKit + `mss` → `temp_disk/<session>/frame_<timestamp>.png`.  
2. **Label:** Gemini 2.0 Flash → `activity_type`, `technical_context`, `alignment_score`, `is_deep_work`, `active_app`, `window_title`.  
3. **Buffer:** `collections.deque(maxlen=180)` per session holds ~30 minutes; popping deletes the screenshot.  
4. **Sync:** Deep work entries → MongoDB Atlas via `HiveMindClient`.  
5. **Query:** Oracle UI pulls scoped history from Atlas and feeds it to Gemini for answer synthesis.

### Component Map

| File | Role |
|------|------|
| `src/monitor.py` | Dual-context capture, Gemini prompting, privacy filter, Hive Mind sync. |
| `src/session.py` | Data model for multi-session buffers, temp folders, git roots. |
| `src/ui.py` | Mission Control (sessions/logs) + Hive Mind Oracle tab. |
| `src/triggers.py` | Per-session git watcher emitting `.devscope/context-<hash>.md`. |
| `src/db.py` | MongoDB Atlas client (publish/query). |
| `src/oracle.py` | RAG wrapper that turns Hive Mind history into natural language answers. |
| `scripts/ghost_team.py` | Synthetic personas (Alice, Bob) for demo seeding. |

Example metadata stored in MongoDB:
```json
{
  "timestamp": "2025-11-22T18:14:52Z",
  "task": "Debugging",
  "summary": "Debugging Stripe Error 409",
  "technical_context": "payments/api.py:422",
  "app_name": "VS Code",
  "active_app": "VS Code",
  "window_title": "auth.py — DevScope",
  "alignment_score": 92,
  "is_deep_work": true,
  "user_id": "naman",
  "org_id": "demo-org",
  "project_name": "Payments-API"
}
```

---

## 🎬 Demo Walkthrough (Script)

1. **Scene 1 – The Capture:** You’re untangling a gnarly React bug—VS Code, docs, StackOverflow tabs everywhere. DevScope quietly records the dual-context stream.  
2. **Scene 2 – The Interruption:** Teammate “Alice” needs status but refuses to break your flow; she opens the Hive Mind tab.  
3. **Scene 3 – The Query:** Alice asks, “How did the team fix the React rendering issue?” and scopes to the Frontend project.  
4. **Scene 4 – The Reveal:** Oracle pulls the last few MongoDB entries, feeds them into Gemini, and answers: “Naman was in React 18 Concurrent Mode docs and patched a re-render loop in `App.js`.” Alice gets context instantly; you never alt-tabbed.

---

## ❓ The Hard Questions (Defense)

| Question | Response |
| --- | --- |
| **Is this spyware?** | No. Screenshots stay local and expire every ~30 min. Only JSON insights marked as deep work are encrypted and synced. |
| **Why MongoDB Atlas?** | Engineering context is messy. Mongo’s flexible document model ingests multimodal metadata (error codes, app names, natural language) without painful schema migrations. |
| **How is this collaborative?** | DevScope enables “Async Omniscience.” Teammates unblock each other by querying the Hive Mind instead of DM’ing for status updates. |
| **What about privacy apps?** | Configure `DEVSCOPE_PRIVACY_APPS="Safari,Notes,1Password"` etc. Blocklisted apps short-circuit capture before frames ever reach disk. |

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
git clone git@github.com:NamanVashishta/DevScope.git
cd DevScope

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

1. Launch the UI, create or select a session, press **Start Session**.  
2. Watch the Visual Ring Buffer populate with dual-context entries (task, active app, deep-work flag).  
3. Trigger a git commit; inspect `.devscope/context-<hash>.md` for the frozen timeline.  
4. Open the Hive Mind tab, seed ghost data if needed (`python scripts/ghost_team.py`).  
5. Ask the Oracle a scoped question and review the synthesized answer plus status log.

---

## 📚 Additional Docs

- [Quick Start](QUICK_START.md) – Fastest path from clone to running the UI.
- [How to Run](HOW_TO_RUN.md) – Detailed runbook with troubleshooting tips.

---

## 🗺️ Roadmap

- [ ] Slack routing per session + automatic context replies.  
- [ ] Buffer analytics (flow vs fragmentation heatmaps).  
- [ ] Privacy-first OCR redaction prior to Gemini upload.  
- [ ] Windows/Linux capture via Win32 & X11 pipelines.  
- [ ] Packaging (PyInstaller/dmg) for one-click installs.

---

## 📄 License

DevScope is released under the [MIT License](LICENSE).

---

## 🏆 Why DevScope Wins

- **Sponsor Alignment:** Heavy use of Gemini 2.0 (vision + text) and MongoDB Atlas (central brain).  
- **Problem Fit:** Directly answers Statement Three by optimizing team workflows and reducing interruption tax.  
- **Scale-Ready:** Multi-session engine, cloud Hive Mind, Oracle UI, and ghost-data seeding turn DevScope into an enterprise-ready collaboration layer.  

**DevScope shifts collaboration from synchronous interruption to asynchronous intelligence.**

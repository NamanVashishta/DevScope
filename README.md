# DevScope – The Visual Cortex for Engineering Teams

DevScope is an agentic layer that automates engineering context. It runs locally on macOS, captures your development workflow through multimodal vision, and turns that stream into actionable collaboration artifacts: protected deep-work time, automated Q&A, and contextualized handoffs.

## The Pitch

> “Software collaboration is broken. We interrupt engineers like routers—asking ‘What are you working on?’ or ‘Where are the API keys?’ Every ping kills flow.  
> DevScope automates context. It maintains a visual memory of the workspace, frees engineers to stay heads-down, and still keeps the team informed.”

- **Protects Flow:** Detects deep work visually and shields the engineer from Slack noise unless it can answer on their behalf.
- **Automates Answers (Visual RAG):** Searches the latest visual buffer to resolve teammate questions (“He was looking at `.env` 5 minutes ago; here’s the snippet.”).
- **Automates Handoffs:** When code is committed, DevScope bundles the last 30 minutes of visual context (logs, docs, fixes) and attaches it to the commit for reviewers.

## Defensive Talking Points

1. **Is this spyware?** No. All screenshots live in a local ring buffer that auto-purges every 30 minutes. Data leaves the device only when the developer explicitly shares it (auto-answer, context report). DevScope is defensive tooling for the maker.
2. **Why call it collaborative if it blocks Slack?** Deep collaboration requires deep work. DevScope blocks interruptions only when it can answer them using the visual history, keeping information flowing asynchronously.
3. **How do you link context to commits?** We watch `.git/logs/HEAD`. When a commit appears, we freeze the buffer and attach that time window to the commit hash.
4. **What about private work?** A privacy allow/deny list prevents sensitive surfaces (e.g., banking apps) from being captured at all. Vision runs locally before anything is stored.

## Architecture Overview

### Hybrid Ring Buffer

DevScope sees everything but only remembers what matters. Screenshots stream into a bounded deque (maxlen 180 ≈ 30 minutes at 10‑second cadence). Once entries roll off, their image files are deleted.

```
Quartz/MSS → temp_disk/<timestamp>.png → Gemini Flash → metadata deque
```

Each buffer entry:
```json
{
  "timestamp": "...",
  "task": "Debugging",
  "app": "VS Code",
  "technical_context": "Error 500 in payments.py",
  "is_deep_work": true,
  "image_path": "temp_disk/..."
}
```

### Component Map

| Component | Purpose |
|-----------|---------|
| `src/monitor.py` | Visual engine: captures the screen every 10 s, sends frames to Gemini 2.0 Flash, stores metadata in the deque, purges old frames, honors privacy lists. |
| `src/triggers.py` | Git watcher (`watchdog`) plus Slack watcher (`slack_sdk`). Git commits → Markdown context reports. Slack DMs + `is_deep_work` → Gemini-powered auto replies. |
| `src/ui.py` | PyQt5 + `qt-material` control panel. Select repo, start/stop session, inspect live status (buffer entries, trigger actions). |
| `src/api_models.py` | Gemini client wrapper (already present) reused for visual labeling. |
| `src/utils.py` | macOS capture pipeline (Quartz + MSS), temp-disk helpers, privacy filters, common logging. |

## Data Flow

1. **Visual capture:** `monitor.py` calls the Quartz/MSS pipeline (from `utils.py`) every 10 seconds (configurable), writes frames to `temp_disk/`.
2. **Labeling:** Each frame is sent to Gemini 2.0 Flash for lightweight tags (`task`, `app`, `technical_context`, `is_deep_work`).
3. **Ring buffer:** Metadata + file path stored inside `collections.deque(maxlen=180)`. When an entry is dropped, its image is deleted.
4. **Triggers:**  
   - **Git:** `watchdog` monitors `.git/logs/HEAD`. On change (commit), DevScope snapshots the buffer, renders a Markdown “Context Report” (recent images, textual summary), and saves it alongside the repo.  
   - **Slack:** `slack_sdk` listens for DMs. If the buffer shows `is_deep_work=True`, DevScope asks Gemini whether it can answer based on visual history. If yes, it auto-replies and logs the action.
5. **UI:** PyQt5 dashboard spawns worker threads for monitor + triggers, displays last labels, buffer fill, and trigger activity. Theme: qt-material “Dark Teal”.

## Privacy Model

- **Local ring buffer:** Stored in-memory plus tmp PNGs, purged after 30 minutes.
- **Explicit sharing:** Only triggered by auto-answer or commit context; otherwise data never leaves the device.
- **Privacy filters:** Blocklisted apps/URLs are skipped before capture (`DEVSCOPE_PRIVACY_APPS="Safari,Notes"`). Future work includes dynamic OCR-based redaction.

## Setup

### Requirements

- macOS Sequoia/Sonoma with screen-recording permission.
- Python 3.10+ (recommend Homebrew install).
- Google Gemini API key (`GEMINI_API_KEY`).
- Slack bot token (`SLACK_BOT_TOKEN`) with DM scope (for auto replies).
- Optional: `ELEVEN_LABS_API_KEY` if you keep legacy TTS hooks.
- `qt-material`, `watchdog`, `slack_sdk`, `mss`, `PyQt5`, `google-generativeai`.

### Quick Start

```bash
git clone <repo>
cd Transparent-Focus-Agent
python3 -m venv focusenv && source focusenv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY=...
export SLACK_BOT_TOKEN=xoxb-...
python3 src/ui.py
```

Grant Screen Recording under System Settings → Privacy & Security → Screen Recording for Terminal/Python.

### Configuring DevScope

- **Project folder**: select inside the UI; DevScope watches its `.git/logs/HEAD`.
- **Capture cadence**: default 10 s; lower for more fidelity, higher to save cost.
- **Privacy list**: define in `privacy.yaml` (coming soon) to skip sensitive domains/apps.
- **Slack auto-answer**: toggle in UI. Requires bot token configured.

## Demo Script

1. Open DevScope UI, select a repo, press Start.
2. Show live buffer entries updating (task/app labels).
3. Trigger a Slack DM from a teammate; show DevScope auto-answering with visual context.
4. Make a git commit; display generated Markdown context report.

## Roadmap

- Buffer analytics (heatmaps of tasks, time-in-deep-work).
- Commit hooks to attach context reports automatically.
- Privacy-first OCR scrubbing before storage.
- Cross-platform capture (Windows/Linux) with OS-specific hooks.
- Packaging (PyInstaller/dmg) for one-click install.

## License

Add your preferred license.

---

**DevScope shifts collaboration from synchronous interruption to asynchronous intelligence.**

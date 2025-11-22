# Aura - The AI Focus Partner
## 🔍 Overview

**Aura** is a macOS-native desktop application that acts as an intelligent, context-aware focus partner. Unlike traditional site blockers that work on simple URL blacklists, Aura uses **multimodal AI vision** to understand *what you're actually doing* on your screen—not just what app you're using.

### The Magic: Visual Context Understanding

Aura's "magic" is that it's not a "dumb" blocker. It's **smart enough to understand visual context**. For example:
- ✅ Watching a coding tutorial on YouTube → **Productive** (allowed)
- ❌ Watching entertainment videos on YouTube → **Procrastinating** (nudged)
- ✅ Reading `reddit.com/r/latex` for your HCI paper → **Productive** (allowed)
- ❌ Browsing `reddit.com/r/funny` → **Procrastinating** (nudged)

Aura sees the *actual content* on your screen, not just the application name. This makes it fundamentally different from any other productivity tool.

### How It Works

Aura works by taking screenshots of your active window every few seconds (at a configurable interval) and feeding them into a multimodal AI model (Gemini 2.0 Flash). The AI analyzes the *visual content* on your screen along with your session goal to determine if you're being productive or procrastinating.

Before every Aura session, you specify:
- **Your Goal:** What you're planning to work on (e.g., "Finish my HCI paper")
- **Allowed Behaviors:** What's considered productive (e.g., "Stack Overflow, GitHub, React docs, coding tutorials on YouTube")
- **Blocked Behaviors:** What's considered procrastination (e.g., "Social media, entertainment videos, games")

Aura can handle nuanced rules such as *"I'm allowed to go on YouTube, but only to watch Karpathy's lecture on Makemore"*. No other productivity software can handle this level of flexibility because they can't see the actual content—only the application name.

### It's Alive!

A big design goal with Aura is that it should *feel alive*. In practice, users tend not to break the rules because they can intuitively *feel* the AI watching them—just like how test-takers are much less likely to cheat when they can *feel* someone watching them. The real-time monitoring creates a psychological presence that helps maintain focus.

## 🚀 Setup and Installation

**This build is macOS-only.** All scripts and docs below assume you are on macOS Sequoia/Sonoma (Apple Silicon or Intel).

### macOS

```bash
git clone <your-repo-url>
cd Transparent-Focus-Agent
chmod +x run.sh  # Make script executable (if needed)
./run.sh
```

**For detailed macOS setup, see [MAC_SETUP.md](MAC_SETUP.md)** and the mac-specific [QUICK_START.md](QUICK_START.md).

**Note:** On macOS, you'll need to grant Screen Recording permission in System Settings → Privacy & Security → Screen Recording.

### API Keys

Define these environment variables before launching Aura:
- `GEMINI_API_KEY` - Required for Gemini 2.0 Flash (free tier available)
- `ELEVEN_LABS_API_KEY` - Optional, enables text-to-speech alerts

**💡 Cost Optimization Tip:** Increase `delay_time` (e.g., 5–10 seconds) to reduce screenshot frequency and API calls while staying within Gemini’s free tier.


## ✨ Key Features

- **🎯 Visual Context Understanding:** Sees actual content on your screen, not just app names
- **🍏 macOS-Native Flow:** Tuned for macOS permissions, screen capture, and TTS
- **🤖 Gemini-Powered Monitoring:** Tuned specifically for Gemini 2.0 Flash multimodal analysis
- **💰 Cost-Effective:** Gemini Flash stays in the free tier with sensible screenshot intervals
- **⚡ Real-Time Monitoring:** Active window tracking with configurable frequency
- **🎨 Modern GUI:** Beautiful PyQt5 interface with live status indicators
- **🔊 Optional TTS:** Text-to-speech alerts using Eleven Labs
- **📊 Post-Session Analytics:** Analyze your focus patterns (see `analytics.py`)

## ⚙️ Configuration Options

The following settings can be configured in the GUI settings panel or via command-line arguments:

| Setting | Description |
|---------|-------------|
| `model_name` | AI model to use (mac-only build supports `gemini-2.0-flash`) |
| `tts` | Enable Eleven Labs text-to-speech for voice alerts |
| `voice` | Voice selection for TTS (Adam, Arnold, Emily, Harry, Josh, Patrick) |
| `cli_mode` | Run without GUI (command-line only) |
| `delay_time` | Seconds between screenshots (0 = continuous, higher = less frequent) |
| `initial_delay` | Seconds to wait before monitoring starts (time to set up your workspace) |
| `countdown_time` | Seconds given to close distraction after being caught (default: 15) |
| `user_name` | Your name for personalized messages |
| `print_CoT` | Show AI's chain-of-thought reasoning in console |


## 🏗️ Architecture

### Core Components

- **`main.py`** - Main control loop that orchestrates screenshot capture, AI analysis, and intervention triggers
- **`user_interface.py`** - PyQt5 GUI for session setup, live monitoring, and settings management
- **`api_models.py`** - Gemini client wrapper plus shared model orchestration helpers
- **`procrastination_event.py`** - Intervention system with popup windows and countdown timers
- **`utils.py`** - macOS-focused utilities for screenshot capture, text-to-speech, and platform detection
- **`config_prompts.yaml`** - All AI prompts for different roles (judge, heckler, pledge, countdown, etc.)
- **`analytics.py`** - Post-session analysis tools for reviewing focus patterns

### How It Works

1. **Session Setup:** User enters goal and allowed/blocked behaviors in GUI
2. **Active Window Monitoring:** System captures screenshots of active window at configured intervals
3. **AI Analysis:** Screenshots sent to multimodal AI with user's goal for context-aware analysis
4. **Decision Making:** AI determines if activity is "productive" or "procrastinating" based on visual content
5. **Intervention:** If procrastinating, shows popup with personalized message, pledge, and countdown timer
6. **Continuous Loop:** Process repeats until user stops the session

### Generated Files

As the program runs, it creates:
- `settings.json` - Your configuration preferences (auto-created)
- `screenshots/` - Folder containing all captured screenshots (with timestamps)
- `yell_voice.mp3` - TTS audio file (if TTS enabled, created in `src/` folder)

## 🎯 Use Cases

Aura is perfect for:

- **👨‍💻 Software Developers:** Monitor coding sessions, allow Stack Overflow/GitHub/docs, block social media
- **📚 Students:** Study session monitoring, allow educational content, block distractions
- **✍️ Writers:** Writing session focus, allow research materials, block time-wasting sites
- **💼 Remote Workers:** Work session accountability, customizable rules per project, productivity tracking
- **🎓 Researchers:** Deep work sessions with context-aware monitoring

## 🔒 Privacy & Security

- **Local-Only Storage:** All screenshots are stored locally on your machine
- **No Cloud Uploads:** Screenshots never leave your computer
- **No External Tracking:** No analytics or telemetry sent to external servers
- **User Control:** You can delete the `screenshots/` folder at any time
- **API Privacy:** Screenshots are sent to Google (Gemini) for analysis—review their privacy policies

## 🌐 Roadmap and Future Improvements

This project is actively under development. Planned features:

### Short Term
- **System Tray Integration:** Minimize to system tray/menu bar for background operation
- **Session Timers:** Set duration goals (e.g., "Focus for 60 minutes")
- **Whitelist System:** User can mark false positives as "work-related" to prevent repeat nudges
- **Native Notifications:** Optional native OS notifications (less intrusive than popups)
- **Post-Session Coach:** AI-generated performance review after each session

### Medium Term
- **Session Scheduling:** Auto-start when you open your computer
- **Enhanced Analytics:** Full integration of post-session analysis into main UI
- **Draft Sessions:** Save and reuse common session configurations
- **Fine-Tuned Models:** Tailored Gemini prompt packs for niche workflows
- **Hybrid Monitoring:** Combine window title tracking with visual analysis for cost optimization

### Long Term
- **Multi-Session Tracking:** Track productivity patterns over time
- **Customizable Interventions:** User-defined intervention styles (gentle vs. strict)
- **Team Features:** Share session goals and accountability with teammates
- **Mobile Companion:** Mobile app for session management and quick stats

## 📚 Additional Documentation

- **[QUICK_START.md](QUICK_START.md)** - Get up and running fast on macOS
- **[MAC_SETUP.md](MAC_SETUP.md)** - macOS-specific setup and troubleshooting guide
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - How to test Aura
- **[RATE_LIMIT_GUIDE.md](RATE_LIMIT_GUIDE.md)** - Managing API rate limits
- **[API_KEYS_EXPLAINED.md](API_KEYS_EXPLAINED.md)** - API key setup guide

## 🤝 Contributing

Contributions are welcome! This project is actively developed and open to improvements. Areas where help is especially appreciated:
- macOS testing across Sequoia/Sonoma hardware
- Cost optimization strategies
- UI/UX improvements
- Documentation enhancements

## 📄 License

[Add your license here]

---

**Built with ❤️ for people who want to do deep work, but need a little help staying focused.**

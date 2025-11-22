# API Keys (Mac Build)

Aura’s mac-only build now runs exclusively on **Gemini 2.0 Flash**, so setup is simple: you only need the Gemini key plus (optionally) an Eleven Labs key for voice heckling.

## Required

1. **`GEMINI_API_KEY`**  
   - Get it: https://aistudio.google.com/app/apikey  
   - Free tier: 15 requests/minute, 1M tokens/minute  
   - Export it in your shell before running `./run.sh`

## Optional

2. **`ELEVEN_LABS_API_KEY`**  
   - Enables spoken heckles/countdown narration  
   - Skip it if you keep TTS disabled in Settings  
   - Get it: https://elevenlabs.io/app/settings/api-keys

## Quick Setup

```bash
export GEMINI_API_KEY="AIza..."
# only if you want TTS
export ELEVEN_LABS_API_KEY="eleven-..."
```

Add those lines to `~/.zshrc` (or your preferred shell profile) so they persist between sessions.

That’s it—no OpenAI, Anthropic, or Ollama keys are used in this build.


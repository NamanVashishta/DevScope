# Aura - Prerequisites Checklist

## ✅ Required Prerequisites

### 1. **Python 3.8 or Higher (macOS)**
   - Check if installed: `python3 --version`
   - Install via Homebrew if needed: `brew install python3`

### 2. **API Keys**

   **Required**  
   - `GEMINI_API_KEY` (Gemini 2.0 Flash, free tier: 15 RPM / 1M TPM)  
   - Get it from: https://aistudio.google.com/app/apikey

   **Optional**  
   - `ELEVEN_LABS_API_KEY` (text-to-speech heckling)  
   - Get it from: https://elevenlabs.io/app/settings/api-keys

## 📋 Quick Prerequisites Checklist

- [ ] Python 3.8+ installed (`python --version` works)
- [ ] `GEMINI_API_KEY` exported in your shell
- [ ] (Optional) `ELEVEN_LABS_API_KEY` exported for TTS

## 🔑 Setting API Keys

### macOS (Terminal or iTerm):
```bash
export GEMINI_API_KEY="your-key-here"
export ELEVEN_LABS_API_KEY="your-key-here"  # optional

# Verify
echo $GEMINI_API_KEY
```

### Permanent Setup (macOS):
Add the exports above to `~/.zshrc` (or `~/.bash_profile`), then reload:
```bash
echo 'export GEMINI_API_KEY="your-key-here"' >> ~/.zshrc
source ~/.zshrc
```

## 🚀 Ready to Deploy?

Once you have:
1. ✅ Python installed
2. ✅ At least one API key set

You're ready! Run the macOS launcher:
- ```bash
  ./run.sh
  ```

## 💡 Recommended First-Time Setup

- Start with `gemini-2.0-flash`
- Set `delay_time` to 5–10 seconds to stay in the free tier
- Leave TTS off unless you’ve added the Eleven Labs key


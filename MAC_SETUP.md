# Aura - The AI Focus Partner - macOS Setup Guide

This guide will help you set up and run Aura on macOS.

## 📋 Prerequisites

1. **Python 3.8 or higher**
   - Check if installed: `python3 --version`
   - If not installed, use Homebrew: `brew install python3`
   - Or download from [python.org](https://www.python.org/downloads/)

2. **API Keys**
   - `GEMINI_API_KEY` - Required for Gemini 2.0 Flash
   - `ELEVEN_LABS_API_KEY` - Optional for text-to-speech heckling

## 🚀 Quick Start

### Method 1: Using the Shell Script (Recommended)

1. Open Terminal in the project directory
2. Make sure the script is executable (if not already):
   ```bash
   chmod +x run.sh
   ```
3. Run:
   ```bash
   ./run.sh
   ```

The script will:
- Create a virtual environment automatically (`focusenv`)
- Install all dependencies
- Start the GUI

### Method 2: Manual Setup

1. Create a virtual environment:
   ```bash
   python3 -m venv focusenv
   ```

2. Activate the virtual environment:
   ```bash
   source focusenv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set environment variables (see below)

5. Run the application:
   ```bash
   python3 src/user_interface.py
   ```

## 🔑 Setting API Keys

### Export Keys (Zsh/Bash)

```bash
export GEMINI_API_KEY="your-key-here"
export ELEVEN_LABS_API_KEY="your-key-here"  # optional
```

Make them persistent by appending the same lines to `~/.zshrc` (or `~/.bash_profile`) and reloading your shell with `source ~/.zshrc`.

## 🔐 macOS Permissions

**Important:** macOS requires screen recording permissions for Aura to work.

1. When you first run Aura, macOS will prompt you for screen recording permission
2. Go to **System Settings** → **Privacy & Security** → **Screen Recording**
3. Find "Terminal" (or "Python" if running directly) in the list
4. Enable the toggle to allow screen recording
5. Restart the application after granting permission

**Note:** If you're running from an IDE or different terminal, you may need to grant permission to that application instead.

## ⚙️ Configuration

### Default Settings

The application uses these default settings (customizable in Settings):
- **Model**: Gemini 2.0 Flash
- **Screenshot Delay**: 0 seconds (screenshots continuously)
- **Initial Delay**: 0 seconds
- **Countdown Time**: 15 seconds
- **TTS**: Disabled

### Customization

1. **Model Selection**: Fixed to Gemini in this mac build
2. **Screenshot Frequency**: Adjust "Delay Time" between screenshots (in seconds)
3. **Text-to-Speech**: Enable TTS and choose from 6 different voices

### Settings Location

Settings are saved in `settings.json` in the project root. You can edit this file directly or use the Settings button in the GUI.

## 📸 Screenshots

Screenshots are automatically saved to the `screenshots/` folder in the project root. Each screenshot is named with the format: `active_window_{timestamp}.png` or `screen_{monitor_number}_{timestamp}.png`

## 🛠️ Troubleshooting

### Issue: "Python is not recognized" or "python3: command not found"

**Solution**: 
- Make sure Python 3 is installed: `python3 --version`
- If using Homebrew: `brew install python3`
- Try using the full path: `/usr/bin/python3` or `/usr/local/bin/python3`

### Issue: "Failed to install dependencies"

**Solution**:
- Make sure you're using Python 3.8 or higher
- Try upgrading pip: `python3 -m pip install --upgrade pip`
- Install Xcode Command Line Tools: `xcode-select --install`
- Some packages may require additional system libraries

### Issue: "No screens detected" or "Failed to capture active window"

**Solution**:
- **Grant Screen Recording Permission** (see macOS Permissions section above)
- Make sure you've granted permission to Terminal (or your IDE)
- Restart the application after granting permission
- Check System Settings → Privacy & Security → Screen Recording

### Issue: "AppKit not available" or "ImportError: No module named 'AppKit'"

**Solution**:
- Make sure `pyobjc` is installed: `pip install pyobjc`
- Install all dependencies: `pip install -r requirements.txt`
- The `requirements.txt` includes all necessary pyobjc frameworks

### Issue: Screenshot functionality not working

**Solution**:
- **Most common issue**: Screen recording permission not granted (see macOS Permissions)
- Make sure `mss` library is installed: `pip install mss`
- Try running the application from Terminal (not IDE) to ensure proper permissions
- Check that `screencapture` command works: `screencapture -x test.png`

### Issue: API calls failing

**Solution**:
- Verify your Gemini key is set correctly: `echo $GEMINI_API_KEY`
- Check your Gemini usage quotas
- Make sure you have internet connectivity

### Issue: TTS not working

**Solution**:
- Verify `ELEVEN_LABS_API_KEY` is set: `echo $ELEVEN_LABS_API_KEY`
- Check that you have audio output device connected
- Test audio playback: `python3 -c "import sounddevice; print(sounddevice.query_devices())"`
- Make sure `sounddevice` and `soundfile` are installed

### Issue: PyQt5 installation fails

**Solution**:
- Install system dependencies: `brew install pyqt5` (if using Homebrew)
- Or try: `pip install --upgrade pip setuptools wheel`
- Then: `pip install PyQt5`

## 🎯 Usage Tips

1. **Cost Management**: 
   - Use Gemini 2.0 Flash (free tier)
   - Adjust screenshot frequency to reduce API calls

2. **Performance**:
   - Higher screenshot frequency = more accurate but more expensive
   - Lower screenshot frequency = cheaper but may miss brief distractions
   - Recommended: 5-10 seconds delay for balance

3. **Privacy**:
   - Screenshots are stored locally in `screenshots/` folder
   - Delete screenshots regularly if privacy is a concern
   - API calls send screenshots to cloud services (check their privacy policies)

## 📝 Technical Notes

- macOS uses `screencapture` command and `AppKit` framework for screenshots
- The application automatically detects macOS and uses the appropriate methods
- Active window capture uses `screencapture -w` flag
- Full screen capture uses `screencapture -D{monitor}` for multi-monitor setups
- Falls back to MSS library if AppKit is not available

## 🆘 Getting Help

If you encounter issues:
1. Check the troubleshooting section above
2. Review the main README.md for general information
3. Check that all dependencies are correctly installed
4. Verify your Python version: `python3 --version` (should be 3.8+)
5. Make sure screen recording permission is granted

## 🔄 Updates

To update Aura:
1. Pull latest changes from repository
2. Activate virtual environment: `source focusenv/bin/activate`
3. Run: `pip install -r requirements.txt --upgrade`
4. Restart the application


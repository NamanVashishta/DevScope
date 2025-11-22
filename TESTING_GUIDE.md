# Aura Testing Guide

## 🚀 Quick Test Setup

### Step 1: Launch Aura
```bash
cd /path/to/Transparent-Focus-Agent
export GEMINI_API_KEY="AIzaSyDOYHBRDeLMNtB7r5c8wPG9sJdjh5F3pXI"
./run.sh
```

### Step 2: Enter a Test Task
When the GUI opens, type something like:
```
I'm testing Aura. 
Allowed: VS Code, documentation sites
Not allowed: YouTube, Twitter, Reddit, any social media
```

### Step 3: Click "Start Focus Session"

---

## ✅ Test Checklist

### Test 1: Basic Functionality
- [ ] GUI opens without errors
- [ ] Can type in the task description box
- [ ] "Start Focus Session" button works
- [ ] Settings button (⚙) opens settings dialog
- [ ] Timer starts counting up

### Test 2: Active Window Capture
- [ ] Open any window (VS Code, browser, etc.)
- [ ] Check `screenshots` folder - should see `active_window_*.png` files
- [ ] Screenshots should only show the active/focused window
- [ ] Screenshots should be created every 5 seconds (default delay)

### Test 3: Procrastination Detection
**To trigger procrastination:**
1. Start a focus session with the task above
2. Open YouTube, Twitter, Reddit, or any social media
3. Wait 5-10 seconds (one or two screenshot cycles)
4. Aura should detect you're procrastinating

**Expected behavior:**
- [ ] Full-screen popup appears with Aura message
- [ ] Popup shows snarky/heckler message
- [ ] Shows a large button: "✓ I Understand - Let Me Get Back to Work"
- [ ] Button works when clicked (no typing required!)
- [ ] Countdown timer appears (15 seconds by default)
- [ ] Countdown counts down: 15, 14, 13... 1, "Time's Up!"
- [ ] Countdown window auto-closes when done

### Test 4: Productivity Detection
**To test productive state:**
1. Start a focus session
2. Keep VS Code or allowed application open
3. Wait 5-10 seconds
4. Check the output in the main window

**Expected behavior:**
- [ ] Output shows: "Gemini 2.0 Flash Determination: productive" (or similar)
- [ ] No popup appears
- [ ] Session continues normally

### Test 5: Settings
- [ ] Open Settings (⚙ button or Cmd+S)
- [ ] Model dropdown shows `gemini-2.0-flash`
- [ ] Change delay time - should save
- [ ] Change countdown time - should save
- [ ] Settings persist when you restart Aura

---

## 🎯 Quick Test Scenarios

### Scenario 1: Test Detection (Fast)
1. Start session with: `"Testing. Not allowed: YouTube, Twitter"`
2. Immediately open YouTube
3. Wait ~5 seconds
4. Should see procrastination popup

### Scenario 2: Test Active Window
1. Start session
2. Open VS Code (allowed)
3. Open YouTube in background (not visible)
4. VS Code is active window
5. Should NOT detect procrastination (only sees VS Code)

### Scenario 3: Test Button Instead of Typing
1. Trigger procrastination popup
2. Click the big button instead of typing
3. Should work instantly
4. Countdown should appear

### Scenario 4: Test Countdown Auto-Close
1. Trigger procrastination
2. Click acknowledge button
3. Watch countdown
4. Should auto-close when it reaches 0

---

## 📊 What to Check

### Console Output
Look for these messages:
```
✅ Gemini 2.0 Flash Determination: productive
❌ Gemini 2.0 Flash Determination: procrastinating
```

### Screenshots Folder
- Location: `<repo-root>/screenshots/`
- Should contain: `active_window_YYYYMMDD_HHMMSS.png`
- Check if screenshots are correct (active window only)

### UI Elements
- Main window should have modern dark theme
- Buttons should have hover effects
- Popup should have dark theme with blue accents
- Countdown should be styled with large red numbers

---

## 🐛 Troubleshooting Tests

### If procrastination is NOT detected:
- Check console for "Determination: productive" 
- Verify you're on a site that's clearly procrastination
- Try making the delay shorter (Settings → Delay Time = 2 seconds)
- Make your task description more explicit about what's not allowed

### If popup doesn't appear:
- Check console for errors
- Verify the determination says "procrastinating"
- Try restarting Aura

### If countdown doesn't auto-close:
- Check console for errors
- Wait a bit longer - it should close after showing "Time's Up!"
- If stuck, manually close it and report

### If active window capture fails:
- Check console for warnings
- Falls back to full screen automatically
- Verify `pyobjc` is installed: `pip show pyobjc`

---

## ⚡ Quick Test Commands

**Test active window capture:**
```bash
cd /path/to/Transparent-Focus-Agent
source focusenv/bin/activate
python -c "from src.utils import take_screenshot_active_window; print(take_screenshot_active_window())"
```
Should create a screenshot in `screenshots` folder.

**Test settings:**
Check `settings.json` file after changing settings - should update automatically.

**Test API connection:**
```bash
export GEMINI_API_KEY="AIzaSyDOYHBRDeLMNtB7r5c8wPG9sJdjh5F3pXI"
python -c "import google.generativeai as genai; genai.configure(api_key='$GEMINI_API_KEY'); print('✅ API Key works!')"
```

---

## 🎉 Success Criteria

You'll know everything works when:
1. ✅ GUI opens and looks modern
2. ✅ Can start a session
3. ✅ Screenshots are being taken (check folder)
4. ✅ Opening YouTube/Twitter triggers popup
5. ✅ Button click works (no typing needed)
6. ✅ Countdown appears and auto-closes
7. ✅ Opening VS Code doesn't trigger (productive)

---

## 💡 Pro Tips for Testing

- **Make delay time short** (2-3 seconds) for faster testing
- **Use obvious sites** (YouTube, Twitter) for reliable detection
- **Check screenshots folder** to verify active window capture
- **Keep console visible** to see determinations in real-time
- **Test in Settings** - enable/disable features to see changes


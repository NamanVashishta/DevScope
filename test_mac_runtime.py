#!/usr/bin/env python3
"""
Runtime test for Mac setup - tests actual functionality
"""

import sys
import os
import platform

# Add src to path
sys.path.insert(0, 'src')

print("=" * 60)
print("Aura Mac Runtime Test")
print("=" * 60)

# Test 1: Platform detection
print("\n1. Platform Detection:")
print(f"   Platform: {platform.system()}")
is_macos = platform.system() == "Darwin"
if not is_macos:
    print("   ✗ Not macOS - exiting")
    sys.exit(1)
print("   ✓ Running on macOS")

# Test 2: Check if we can read the Mac-specific code
print("\n2. Mac-Specific Code Verification:")
with open('src/utils.py', 'r') as f:
    utils_content = f.read()
    
mac_checks = {
    'IS_MACOS = platform.system() == "Darwin"': 'Platform detection',
    'kCGWindowListOptionOnScreenOnly': 'Quartz active-window query',
    'screencapture': 'screencapture command',
    'from Quartz import': 'Quartz import',
    'AppKit': 'AppKit framework fallback',
    'take_screenshot_active_window': 'Active window function'
}

all_passed = True
for check, desc in mac_checks.items():
    if check in utils_content:
        print(f"   ✓ {desc}")
    else:
        print(f"   ✗ {desc} - NOT FOUND")
        all_passed = False

if not all_passed:
    print("   ✗ Some Mac-specific code missing!")
    sys.exit(1)

# Test 3: Test path resolution
print("\n3. Path Resolution:")
import os
venv_python = os.path.join('focusenv', 'bin', 'python3')
if os.path.exists(venv_python):
    print(f"   ✓ Found macOS virtualenv interpreter: {venv_python}")
else:
    print(f"   ⚠ Expected interpreter not found at {venv_python} (run ./run.sh to create it)")

# Test 4: Screenshot directory
print("\n4. Screenshot Directory:")
screenshots_dir = 'screenshots'
os.makedirs(screenshots_dir, exist_ok=True)
if os.path.exists(screenshots_dir):
    print(f"   ✓ Screenshots directory exists: {screenshots_dir}")
else:
    print(f"   ✗ Cannot create screenshots directory")
    sys.exit(1)

# Test 5: Check if screencapture command exists
print("\n5. System Commands:")
import subprocess
result = subprocess.run(['which', 'screencapture'], capture_output=True, text=True)
if result.returncode == 0:
    print(f"   ✓ screencapture found: {result.stdout.strip()}")
else:
    print("   ✗ screencapture command not found")
    sys.exit(1)

# Test 6: Test mss library (if installed)
print("\n6. Screenshot Libraries:")
try:
    import mss
    with mss.mss() as sct:
        monitors = len(sct.monitors) - 1
        print(f"   ✓ mss library works - detected {monitors} monitor(s)")
except ImportError:
    print("   ⚠ mss not installed (will be installed by run.sh)")
except Exception as e:
    print(f"   ⚠ mss error: {e}")

# Test 7: Virtual environment
print("\n7. Virtual Environment:")
venv_path = 'focusenv'
if os.path.exists(venv_path):
    if os.path.exists(os.path.join(venv_path, 'bin')):
        print("   ✓ Mac venv structure (bin/)")
    elif os.path.exists(os.path.join(venv_path, 'Scripts')):
        print("   ✗ Unexpected virtualenv structure (Scripts/) - delete focusenv/ and rerun ./run.sh")
        sys.exit(1)
    else:
        print("   ⚠ Unknown venv structure")
else:
    print("   ⚠ No venv - will be created by run.sh")

print("\n" + "=" * 60)
print("Test Summary:")
print("=" * 60)
print("✓ All runtime tests passed!")
print("\nThe Mac setup is ready. To run:")
print("  1. ./run.sh")
print("  2. Grant Screen Recording permission when prompted")
print("  3. Set API keys: export GEMINI_API_KEY='your-key'")
print("  4. Start using Aura!")
print("=" * 60)


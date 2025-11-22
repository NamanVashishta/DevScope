#!/usr/bin/env python3
"""
Test script to validate Mac setup for Aura
This checks platform detection, imports, and basic functionality
"""

import sys
import os
import platform
import subprocess

print("=" * 60)
print("Aura Mac Setup Test")
print("=" * 60)

# Test 1: Platform detection
print("\n1. Platform Detection:")
print(f"   Platform: {platform.system()}")
is_macos = platform.system() == "Darwin"
print(f"   Is macOS: {is_macos}")
if is_macos:
    print("   ✓ Running on macOS")
else:
    print("   ✗ Not running on macOS - this test is for Mac only")
    sys.exit(1)

# Test 2: Python version
print("\n2. Python Version:")
python_version = sys.version_info
print(f"   Python: {python_version.major}.{python_version.minor}.{python_version.micro}")
if python_version >= (3, 8):
    print("   ✓ Python version is 3.8+")
else:
    print("   ✗ Python version is too old (need 3.8+)")
    sys.exit(1)

# Test 3: screencapture command
print("\n3. Screenshot Command:")
screencapture_path = "/usr/sbin/screencapture"
if os.path.exists(screencapture_path):
    print(f"   ✓ screencapture found at {screencapture_path}")
else:
    result = subprocess.run(["which", "screencapture"], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"   ✓ screencapture found at {result.stdout.strip()}")
    else:
        print("   ✗ screencapture command not found")
        sys.exit(1)

# Test 4: Code structure
print("\n4. Code Structure:")
utils_path = "src/utils.py"
ui_path = "src/user_interface.py"
main_path = "src/main.py"

if os.path.exists(utils_path):
    print("   ✓ utils.py exists")
    with open(utils_path, 'r') as f:
        utils_content = f.read()
        if "IS_MACOS" in utils_content:
            print("   ✓ macOS detection constant found")
        if "IS_WINDOWS" in utils_content:
            print("   ✗ Legacy cross-platform constant detected; please remove it")
            sys.exit(1)
        if "screencapture" in utils_content:
            print("   ✓ screencapture usage found")
        if "AppKit" in utils_content:
            print("   ✓ AppKit import code found")
else:
    print("   ✗ utils.py not found")
    sys.exit(1)

if os.path.exists(ui_path):
    print("   ✓ user_interface.py exists")
    with open(ui_path, 'r') as f:
        ui_content = f.read()
        if '"focusenv", "bin"' in ui_content:
            print("   ✓ macOS virtualenv path handling found")
        else:
            print("   ⚠ Could not verify macOS venv path logic")
else:
    print("   ✗ user_interface.py not found")
    sys.exit(1)

if os.path.exists(main_path):
    print("   ✓ main.py exists")
else:
    print("   ✗ main.py not found")
    sys.exit(1)

# Test 5: Requirements file
print("\n5. Dependencies:")
requirements_path = "requirements.txt"
if os.path.exists(requirements_path):
    print("   ✓ requirements.txt exists")
    with open(requirements_path, 'r') as f:
        req_content = f.read()
        if "pyobjc" in req_content.lower():
            print("   ✓ pyobjc found in requirements (needed for macOS)")
        if "PyQt5" in req_content:
            print("   ✓ PyQt5 found in requirements")
        if "mss" in req_content:
            print("   ✓ mss found in requirements (screenshot library)")
else:
    print("   ✗ requirements.txt not found")
    sys.exit(1)

# Test 6: Run script
print("\n6. Launch Script:")
run_script = "run.sh"
if os.path.exists(run_script):
    print("   ✓ run.sh exists")
    if os.access(run_script, os.X_OK):
        print("   ✓ run.sh is executable")
    else:
        print("   ⚠ run.sh is not executable (run: chmod +x run.sh)")
    with open(run_script, 'r') as f:
        script_content = f.read()
        if "python3" in script_content:
            print("   ✓ Uses python3")
        if "venv" in script_content:
            print("   ✓ Creates virtual environment")
        if "requirements.txt" in script_content:
            print("   ✓ Installs from requirements.txt")
else:
    print("   ✗ run.sh not found")
    sys.exit(1)

# Test 7: Virtual environment (if exists)
print("\n7. Virtual Environment:")
venv_path = "focusenv"
if os.path.exists(venv_path):
    print("   ⚠ Virtual environment exists")
    if os.path.exists(os.path.join(venv_path, "bin")):
        print("   ✓ Mac/Linux venv structure (bin/)")
    elif os.path.exists(os.path.join(venv_path, "Scripts")):
        print("   ⚠ Legacy venv structure (Scripts/) detected - delete focusenv/ and rerun ./run.sh")
    else:
        print("   ⚠ Unknown venv structure")
else:
    print("   ✓ No venv exists - will be created by run.sh")

# Test 8: Documentation
print("\n8. Documentation:")
if os.path.exists("MAC_SETUP.md"):
    print("   ✓ MAC_SETUP.md exists")
else:
    print("   ⚠ MAC_SETUP.md not found")

if os.path.exists("README.md"):
    print("   ✓ README.md exists")
    with open("README.md", 'r') as f:
        readme_content = f.read()
        if "MAC_SETUP.md" in readme_content:
            print("   ✓ README references MAC_SETUP.md")
else:
    print("   ⚠ README.md not found")

print("\n" + "=" * 60)
print("Test Summary:")
print("=" * 60)
print("✓ All basic checks passed!")
print("\nNext steps:")
print("1. Run: ./run.sh")
print("2. Grant Screen Recording permission when prompted")
print("3. Set your API keys as environment variables")
print("4. Start using Aura!")
print("\nFor detailed setup instructions, see MAC_SETUP.md")
print("=" * 60)


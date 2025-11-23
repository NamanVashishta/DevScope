#!/bin/bash
# macOS launcher script for DevScope
# Activates the virtual environment and starts the new PyQt UI

echo "DevScope"

# Check if virtual environment exists
if [ ! -d "focusenv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv focusenv
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment. Make sure Python 3 is installed."
        exit 1
    fi
fi

# Activate virtual environment
source focusenv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies."
    exit 1
fi

# Start the GUI
echo "Starting DevScope..."
python3 src/ui.py

# Deactivate virtual environment when done
deactivate

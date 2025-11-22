#!/bin/bash
# Quick setup script for Gemini API key on Mac

echo "Setting up Gemini API key..."

# Add to .zshrc
if ! grep -q "GEMINI_API_KEY" ~/.zshrc 2>/dev/null; then
    echo 'export GEMINI_API_KEY="your-gemini-api-key"' >> ~/.zshrc
    echo "✓ Added GEMINI_API_KEY to ~/.zshrc"
else
    echo "⚠ GEMINI_API_KEY already exists in ~/.zshrc"
fi

# Set for current session (replace with your key)
export GEMINI_API_KEY="your-gemini-api-key"
echo "✓ Set GEMINI_API_KEY for current session"

echo ""
echo "Configuration:"
echo "  Model: gemini-2.0-flash"
echo "  Delay: 60 seconds (1 request/minute)"
echo "  Rate limit: 15 requests/minute (free tier)"
echo ""
echo "To use:"
echo "  1. source ~/.zshrc  (or restart terminal)"
echo "  2. ./run.sh"


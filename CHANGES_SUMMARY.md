# Aura - The AI Focus Partner - Summary of Changes

This fork converts Aura into a macOS-only distribution. Key updates:

## 1. macOS-First Runtime
- `run.sh` is now the sole launcher; every `.ps1`/`.bat` helper was removed.
- All provisioning paths assume `focusenv/bin/python3` (Apple Silicon + Intel).
- The codebase still contains cross-platform guards, but this build targets macOS exclusively.

## 2. Documentation Refresh
- `README.md`, `QUICK_START.md`, `HOW_TO_RUN.md`, `PREREQUISITES.md`, and `COMPLETE_PREREQUISITES.md` were rewritten for mac workflows.
- Legacy multi-OS guides (`DEPLOYMENT.md`, PowerShell quick starts, prior prerequisite docs) were deleted to prevent stale instructions.
- `MAC_SETUP.md`, `RATE_LIMIT_GUIDE.md`, and `API_KEYS_EXPLAINED.md` are the primary references.

## 3. File Pruning
- Removed legacy scripts: `run.ps1`, `run.bat`, `setup-gemini*.ps1`, `launch-gemini*.ps1`, `setup-conda-env.ps1`, `fix-pyqt5.ps1`.
- Deleted redundant OS-specific requirements files and any assets that existed solely to support non-mac deployments.

## 4. Gemini-Only Model Support
- Removed OpenAI, Anthropic, and Ollama integrations; Aura now runs exclusively on Gemini 2.0 Flash.
- Simplified settings (no router/two-tier toggles) and CLI flags accordingly.
- Updated docs, prerequisites, and requirements to mention only `GEMINI_API_KEY` plus optional Eleven Labs TTS.

## 5. What Remains
- Core Python modules under `src/` (UI, utils, analytics, API clients) are untouched functionally.
- `MAC_SETUP.md` continues to document permissions, Gemini setup, and troubleshooting.
- Generated artifacts (`settings.json`, `screenshots/`, optional TTS audio) still behave exactly the same.

## ✅ Verified
- `./run.sh` provisions `focusenv`, installs dependencies from `requirements.txt`, and launches the GUI on macOS Sequoia.
- Docs now walk users through exporting API keys, granting Screen Recording permission, and starting a focus session without mentioning other OSes.

You now have a clean mac-only package ready for distribution—clone, export keys, run `./run.sh`, and get back to deep work. ✨


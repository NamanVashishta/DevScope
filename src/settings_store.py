import json
from pathlib import Path
from typing import Any, Dict

SETTINGS_DIR = Path.home() / ".devscope"
SETTINGS_PATH = SETTINGS_DIR / "settings.json"

DEFAULT_SETTINGS: Dict[str, str] = {
    "username": "",
    "organization_id": "",
    "project_name": "",
}


def load_settings() -> Dict[str, str]:
    """Read persisted identity settings from disk."""
    if not SETTINGS_PATH.exists():
        return DEFAULT_SETTINGS.copy()
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        merged = DEFAULT_SETTINGS.copy()
        merged.update({k: str(v) for k, v in data.items() if v is not None})
        return merged
    except (OSError, json.JSONDecodeError):
        return DEFAULT_SETTINGS.copy()


def save_settings(settings: Dict[str, Any]) -> None:
    """Persist identity settings to disk."""
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    filtered = {
        "username": settings.get("username", "").strip(),
        "organization_id": settings.get("organization_id", "").strip(),
        "project_name": settings.get("project_name", "").strip(),
    }
    SETTINGS_PATH.write_text(json.dumps(filtered, indent=2), encoding="utf-8")


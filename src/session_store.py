import json
from pathlib import Path
from typing import Any, Dict, List

SETTINGS_DIR = Path.home() / ".devscope"
SESSIONS_PATH = SETTINGS_DIR / "sessions.json"


def load_saved_projects() -> List[Dict[str, Any]]:
    if not SESSIONS_PATH.exists():
        return []
    try:
        data = json.loads(SESSIONS_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [
                {
                    "project_name": str(item.get("project_name", "")),
                    "goal": str(item.get("goal", "")),
                    "repo_path": str(item.get("repo_path", "")),
                }
                for item in data
            ]
    except (json.JSONDecodeError, OSError):
        return []
    return []


def save_projects_state(projects: List[Dict[str, Any]]) -> None:
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "project_name": project.get("project_name", ""),
            "goal": project.get("goal", ""),
            "repo_path": project.get("repo_path", ""),
        }
        for project in projects
    ]
    SESSIONS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

FocusBounds = Tuple[int, int, int, int]


@dataclass
class ActivityRecord:
    """
    Canonical representation of a DevScope activity event.

    Every producer (visual monitor, git trigger, batch summarizer, ghost data)
    should emit this structure so downstream systems can rely on consistent keys.
    """

    timestamp: datetime
    session_id: str
    project_name: str
    session_goal: str
    repo_path: str
    task: str
    activity_type: str
    technical_context: str
    app_name: str
    active_app: str
    window_title: str
    alignment_score: Optional[int]
    is_deep_work: bool
    deep_work_state: str
    privacy_state: str
    focus_bounds: Optional[FocusBounds] = None
    error_code: Optional[str] = None
    function_target: Optional[str] = None
    documentation_title: Optional[str] = None
    doc_url: Optional[str] = None
    screenshot_path: Optional[str] = None
    project_slug: Optional[str] = None
    user_id: Optional[str] = None
    user_display: Optional[str] = None
    org_id: Optional[str] = None
    source: str = "devscope-vision"
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> Dict[str, Any]:
        """
        Convert to a MongoDB-friendly payload while stripping local-only paths.
        """
        payload: Dict[str, Any] = {
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "project_name": self.project_name,
            "project_slug": self.project_slug,
            "session_goal": self.session_goal,
            "repo_path": self.repo_path,
            "task": self.task,
            "activity_type": self.activity_type,
            "technical_context": self.technical_context,
            "error_code": self.error_code,
            "function_target": self.function_target,
            "documentation_title": self.documentation_title,
            "doc_url": self.doc_url,
            "app_name": self.app_name,
            "active_app": self.active_app,
            "window_title": self.window_title,
            "alignment_score": self.alignment_score,
            "is_deep_work": self.is_deep_work,
            "deep_work_state": self.deep_work_state,
            "privacy_state": self.privacy_state,
            "focus_bounds": _bounds_dict(self.focus_bounds),
            "user_id": self.user_id,
            "user_display": self.user_display or self.user_id,
            "org_id": self.org_id,
            "source": self.source,
        }
        # Drop keys whose value is None to keep Mongo docs lean.
        payload = {k: v for k, v in payload.items() if v is not None}
        if self.extra:
            payload.update(self.extra)
        return payload

    def to_ui_dict(self) -> Dict[str, Any]:
        """
        Convert to a JSON-serializable dict for the Mission Control UI.
        """
        data = self.to_payload()
        data["timestamp"] = self.timestamp.isoformat()
        data["screenshot_path"] = self.screenshot_path
        data["project_name"] = self.project_name
        data["session_goal"] = self.session_goal
        data["repo_path"] = self.repo_path
        data["task"] = self.task
        return data


def _bounds_dict(bounds: Optional[FocusBounds]) -> Optional[Dict[str, int]]:
    if not bounds:
        return None
    x, y, width, height = bounds
    return {"x": x, "y": y, "width": width, "height": height}



from __future__ import annotations

from dataclasses import dataclass, field
from collections import deque
from typing import Deque

from activity_schema import ActivityRecord


@dataclass
class Session:
    id: str
    project_name: str
    project_slug: str
    goal: str
    repo_path: str
    temp_dir: str
    ring_buffer: Deque[ActivityRecord] = field(default_factory=deque)


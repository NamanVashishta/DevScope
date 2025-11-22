from __future__ import annotations

from dataclasses import dataclass, field
from collections import deque
from typing import Deque


@dataclass
class Session:
    id: str
    name: str
    goal: str
    repo_path: str
    temp_dir: str
    ring_buffer: Deque = field(default_factory=deque)


from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


@dataclass
class Task:
    id: int
    title: str
    due: Optional[date] = None
    priority: int = 2
    tags: List[str] = field(default_factory=list)
    deps: List[int] = field(default_factory=list)
    status: str = "open"
    done_on: Optional[date] = None
    repeat: Optional[str] = None
    next_id: Optional[int] = None

    @property
    def is_open(self):
        return self.status == "open"

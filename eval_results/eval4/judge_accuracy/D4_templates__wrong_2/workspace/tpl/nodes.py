from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Text:
    text: str


@dataclass
class Var:
    path: str
    filters: list          # [(name, [args])]
    line: int


@dataclass
class For:
    var: str
    path: str
    body: list = field(default_factory=list)
    line: int = 0


@dataclass
class Cond:
    path: str
    op: Optional[str] = None      # None, "==" or "!="
    literal: Any = None
    negate: bool = False


@dataclass
class If:
    branches: list = field(default_factory=list)   # [(Cond or None for else, body)]
    line: int = 0
    has_else: bool = False

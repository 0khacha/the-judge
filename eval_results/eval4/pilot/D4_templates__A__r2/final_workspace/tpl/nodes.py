from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Text:
    text: str


@dataclass
class Filter:
    name: str
    args: list
    line: int


@dataclass
class Var:
    path: str
    filters: list
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
    negated: bool = False
    op: Optional[str] = None      # None, "==" or "!="
    literal: object = None


@dataclass
class Branch:
    cond: Cond
    body: list = field(default_factory=list)
    line: int = 0


@dataclass
class If:
    branches: list = field(default_factory=list)
    else_body: Optional[list] = None
    line: int = 0

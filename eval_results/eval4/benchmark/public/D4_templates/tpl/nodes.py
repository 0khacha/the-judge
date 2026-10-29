from dataclasses import dataclass, field


@dataclass
class Text:
    text: str


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

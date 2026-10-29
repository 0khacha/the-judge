from dataclasses import dataclass, field


@dataclass
class Text:
    text: str


@dataclass
class Var:
    path: str
    filters: list      # [(name, [literal args])]
    line: int


@dataclass
class For:
    var: str
    path: str
    body: list = field(default_factory=list)
    line: int = 0


@dataclass
class Cond:
    negated: bool
    path: str
    op: object         # None (truthiness), "==" or "!="
    value: object      # literal for comparisons


@dataclass
class If:
    branches: list = field(default_factory=list)   # [(Cond, body)]
    else_body: object = None                        # list once an else is seen
    line: int = 0

"""Field definitions."""
from dataclasses import dataclass
from typing import Any

from .coerce import TYPES, coerce


@dataclass
class Field:
    name: str
    type: str = "str"
    required: bool = True
    default: Any = None

    def __post_init__(self):
        if self.type not in TYPES:
            raise ValueError("unknown type %r" % self.type)


class Schema:
    def __init__(self, fields):
        names = [f.name for f in fields]
        if len(set(names)) != len(names):
            raise ValueError("duplicate field names")
        self.fields = list(fields)
        self.names = names

    def field(self, name):
        for f in self.fields:
            if f.name == name:
                return f
        raise KeyError(name)

    def coerce_row(self, values):
        """(row dict, None) or (None, 'field: message')."""
        row = {}
        for f in self.fields:
            text = (values.get(f.name) or "").strip()
            if not text:
                if f.required:
                    return None, "%s: required" % f.name
                row[f.name] = f.default
                continue
            try:
                row[f.name] = coerce(text, f.type)
            except ValueError as exc:
                return None, "%s: %s" % (f.name, exc)
        return row, None


def parse_spec(spec):
    """'id:int,name:str,note:str?' -> Schema."""
    fields = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        name, _, typ = part.partition(":")
        required = not typ.endswith("?")
        typ = typ.rstrip("?") or "str"
        fields.append(Field(name.strip().lower(), typ, required))
    return Schema(fields)

"""The pipeline: read, coerce, de-duplicate, sort."""
from dataclasses import dataclass, field

from .reader import read_rows


class EtlError(Exception):
    """The input or the configuration cannot be processed at all."""


@dataclass
class Reject:
    line: int
    reason: str


@dataclass
class Result:
    rows: list = field(default_factory=list)
    lines: list = field(default_factory=list)       # source line of every accepted row
    rejects: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)


def _key_names(key):
    """None or an empty list/tuple means no key; a string is a single-field key."""
    if key is None:
        return None
    names = [key] if isinstance(key, str) else list(key)
    return names or None


def run(text, schema, key=None, keep="first"):
    if keep not in ("first", "last"):
        raise EtlError("keep must be 'first' or 'last'")
    names = _key_names(key)
    header, raw_rows = read_rows(text)
    missing = [f.name for f in schema.fields if f.required and f.name not in header]
    if missing:
        raise EtlError("missing column(s): %s" % ", ".join(missing))
    if names is not None:
        for name in names:
            if name not in schema.names:
                raise EtlError("unknown key field %s" % name)
            if not schema.field(name).required:
                raise EtlError("key field %s must be required" % name)

    good, rejects = [], []
    for raw in raw_rows:
        if raw.error:
            rejects.append(Reject(raw.line, "line %d: %s" % (raw.line, raw.error)))
            continue
        row, problem = schema.coerce_row(raw.values)
        if problem:
            rejects.append(Reject(raw.line, "line %d: %s" % (raw.line, problem)))
            continue
        good.append((raw.line, row))

    duplicates = superseded = 0
    if names is not None:
        def key_of(row):
            return tuple(row[name] for name in names)

        kept = []
        if keep == "first":
            seen = {}
            for line, row in good:
                k = key_of(row)
                if k in seen:
                    duplicates += 1
                    rejects.append(Reject(line, "line %d: duplicate of line %d" % (line, seen[k])))
                    continue
                seen[k] = line
                kept.append((line, row))
        else:
            successor = {}  # key -> line of the next row with that key (scanning backwards)
            for line, row in reversed(good):
                k = key_of(row)
                if k in successor:
                    duplicates += 1
                    superseded += 1
                    rejects.append(Reject(line, "line %d: superseded by line %d" % (line, successor[k])))
                else:
                    kept.append((line, row))
                successor[k] = line
            kept.reverse()
        good = sorted(kept, key=lambda item: key_of(item[1]))

    rejects.sort(key=lambda r: r.line)
    stats = {
        "read": len(raw_rows),
        "accepted": len(good),
        "rejected": len(rejects),
        "duplicates": duplicates,
        "superseded": superseded,
    }
    return Result([row for _, row in good], [line for line, _ in good], rejects, stats)

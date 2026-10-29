"""The pipeline: read, coerce, de-duplicate, sort."""
from dataclasses import dataclass, field

from .reader import read_rows

KEEP_MODES = ("first", "last")


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
    if key is None:
        return []
    if isinstance(key, str):
        return [key]
    if isinstance(key, (list, tuple)):
        return list(key)
    raise EtlError("key must be a field name or a list of field names")


def run(text, schema, key=None, keep="first"):
    header, raw_rows = read_rows(text)
    missing = [f.name for f in schema.fields if f.required and f.name not in header]
    if missing:
        raise EtlError("missing column(s): %s" % ", ".join(missing))
    keys = _key_names(key)
    for name in keys:
        if name not in schema.names:
            raise EtlError("unknown key field %s" % name)
        if not schema.field(name).required:
            raise EtlError("key field %s must be required" % name)
    if keep not in KEEP_MODES:
        raise EtlError("keep must be 'first' or 'last', not %r" % (keep,))

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

    def group_key(row):
        return tuple(row[name] for name in keys)

    duplicates = superseded = 0
    if keys:
        if keep == "first":
            seen, kept = {}, []
            for line, row in good:
                gk = group_key(row)
                if gk in seen:
                    duplicates += 1
                    rejects.append(Reject(line, "line %d: duplicate of line %d" % (line, seen[gk])))
                    continue
                seen[gk] = line
                kept.append((line, row))
        else:
            current = {}  # group key -> (line, row) of the latest row seen so far
            for line, row in good:
                gk = group_key(row)
                if gk in current:
                    prev_line = current[gk][0]
                    superseded += 1
                    rejects.append(Reject(prev_line, "line %d: superseded by line %d" % (prev_line, line)))
                current[gk] = (line, row)
            kept = list(current.values())
        good = sorted(kept, key=lambda item: group_key(item[1]))

    rejects.sort(key=lambda r: r.line)
    stats = {
        "read": len(raw_rows),
        "accepted": len(good),
        "rejected": len(rejects),
        "duplicates": duplicates + superseded,
        "superseded": superseded,
    }
    return Result([row for _, row in good], [line for line, _ in good], rejects, stats)

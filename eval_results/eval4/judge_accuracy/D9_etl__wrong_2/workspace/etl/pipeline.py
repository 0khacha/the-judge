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
    if key is None:
        return []
    if isinstance(key, str):
        return [key]
    return list(key)


def run(text, schema, key=None, keep="first"):
    if keep not in ("first", "last"):
        raise EtlError("keep must be 'first' or 'last'")
    names = _key_names(key)
    header, raw_rows = read_rows(text)
    missing = [f.name for f in schema.fields if f.required and f.name not in header]
    if missing:
        raise EtlError("missing column(s): %s" % ", ".join(missing))
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
    if names:
        seen, kept = {}, []                      # seen: key tuple -> index in kept
        for line, row in good:
            value = tuple(row[n] for n in names)
            if value in seen:
                duplicates += 1
                slot = seen[value]
                if keep == "first":
                    rejects.append(Reject(line, "line %d: duplicate of line %d" % (line, kept[slot][0])))
                    continue
                old_line = kept[slot][0]
                superseded += 1
                rejects.append(Reject(old_line, "line %d: superseded by line %d" % (old_line, line)))
                kept[slot] = (line, row)
                continue
            seen[value] = len(kept)
            kept.append((line, row))
        good = sorted(kept, key=lambda item: tuple(item[1][n] for n in names))

    stats = {"read": len(raw_rows), "accepted": len(good), "rejected": len(rejects), "duplicates": duplicates,
             "superseded": superseded}
    return Result([row for _, row in good], [line for line, _ in good], rejects, stats)

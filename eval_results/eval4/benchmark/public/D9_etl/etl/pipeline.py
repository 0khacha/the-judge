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


def run(text, schema, key=None):
    header, raw_rows = read_rows(text)
    missing = [f.name for f in schema.fields if f.required and f.name not in header]
    if missing:
        raise EtlError("missing column(s): %s" % ", ".join(missing))
    if key is not None:
        if key not in schema.names:
            raise EtlError("unknown key field %s" % key)
        if not schema.field(key).required:
            raise EtlError("key field %s must be required" % key)

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

    duplicates = 0
    if key is not None:
        seen, kept = {}, []
        for line, row in good:
            value = row[key]
            if value in seen:
                duplicates += 1
                rejects.append(Reject(line, "line %d: duplicate of line %d" % (line, seen[value])))
                continue
            seen[value] = line
            kept.append((line, row))
        good = sorted(kept, key=lambda item: item[1][key])

    rejects.sort(key=lambda r: r.line)
    stats = {"read": len(raw_rows), "accepted": len(good), "rejected": len(rejects), "duplicates": duplicates}
    return Result([row for _, row in good], [line for line, _ in good], rejects, stats)

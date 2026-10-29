"""Output formats."""
import csv
import io
import json
from datetime import date


def _plain(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, date):
        return value.isoformat()
    return value


def to_csv(result, schema):
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(schema.names)
    for row in result.rows:
        writer.writerow([_plain(row[name]) for name in schema.names])
    return buf.getvalue()


def to_jsonl(result, schema):
    lines = []
    for row in result.rows:
        item = {name: (value.isoformat() if isinstance(value, date) else value)
                for name, value in ((n, row[n]) for n in schema.names)}
        lines.append(json.dumps(item))
    return "\n".join(lines) + ("\n" if lines else "")


def rejects_csv(result):
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["line", "reason"])
    for reject in result.rejects:
        writer.writerow([reject.line, reject.reason])
    return buf.getvalue()

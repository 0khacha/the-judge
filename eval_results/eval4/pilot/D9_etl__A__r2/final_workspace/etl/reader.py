"""CSV text -> raw records."""
import csv
import io
from dataclasses import dataclass
from typing import Optional


@dataclass
class RawRow:
    line: int
    values: Optional[dict]
    error: Optional[str] = None


def read_rows(text):
    reader = csv.reader(io.StringIO(text))
    header = None
    rows = []
    for record in reader:
        line = reader.line_num
        if not record or all(not cell.strip() for cell in record):
            continue
        if header is None:
            header = [cell.strip().lower() for cell in record]
            continue
        if len(record) != len(header):
            rows.append(RawRow(line, None, "wrong number of fields"))
            continue
        rows.append(RawRow(line, dict(zip(header, record))))
    return header or [], rows

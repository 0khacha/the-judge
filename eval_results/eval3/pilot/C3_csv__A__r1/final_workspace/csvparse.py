"""Strict CSV parser (standard library only, no ``csv`` module)."""


class CsvError(ValueError):
    """Malformed CSV. ``line`` is the 1-based line number, or None."""

    def __init__(self, message, line=None):
        super().__init__(message)
        self.line = line


def _check_delimiter(delimiter):
    if not isinstance(delimiter, str) or len(delimiter) != 1 or delimiter in '"\r\n':
        raise ValueError(
            "delimiter must be a single character other than '\"', CR or LF"
        )


def _parse_records(text, delimiter):
    """Return a list of (fields, start_line) tuples."""
    _check_delimiter(delimiter)
    if text.startswith("﻿"):
        text = text[1:]

    n = len(text)
    pos = 0
    line = 1
    records = []

    while pos < n:
        # Record start: a bare separator means an empty line, which is skipped.
        ch = text[pos]
        if ch == "\r" or ch == "\n":
            if text.startswith("\r\n", pos):
                pos += 2
            else:
                pos += 1
            line += 1
            continue

        start_line = line
        fields = []
        while True:
            if pos < n and text[pos] == '"':
                quote_line = line
                pos += 1
                buf = []
                closed = False
                while pos < n:
                    c = text[pos]
                    if c == '"':
                        if pos + 1 < n and text[pos + 1] == '"':
                            buf.append('"')
                            pos += 2
                            continue
                        pos += 1
                        closed = True
                        break
                    if c == "\r":
                        if text.startswith("\r\n", pos):
                            buf.append("\r\n")
                            pos += 2
                        else:
                            buf.append("\r")
                            pos += 1
                        line += 1
                        continue
                    if c == "\n":
                        buf.append("\n")
                        pos += 1
                        line += 1
                        continue
                    buf.append(c)
                    pos += 1
                if not closed:
                    raise CsvError(
                        "unterminated quoted field started on line %d" % quote_line,
                        line=quote_line,
                    )
                field = "".join(buf)
                if pos < n and text[pos] not in (delimiter, "\r", "\n"):
                    raise CsvError(
                        "unexpected character %r after closing quote on line %d"
                        % (text[pos], line),
                        line=line,
                    )
            else:
                start = pos
                while pos < n and text[pos] not in (delimiter, "\r", "\n"):
                    pos += 1
                field = text[start:pos]

            fields.append(field)
            if pos < n and text[pos] == delimiter:
                pos += 1
                continue
            break

        # At a record separator or at the end of the text.
        records.append((fields, start_line))
        if pos < n:
            if text.startswith("\r\n", pos):
                pos += 2
            else:
                pos += 1
            line += 1

    return records


def parse_csv(text, delimiter=","):
    """Parse a CSV document into a list of records (lists of strings)."""
    return [fields for fields, _ in _parse_records(text, delimiter)]


def parse_csv_dicts(text, delimiter=","):
    """Parse CSV using the first record as header; return one dict per row."""
    records = _parse_records(text, delimiter)
    if not records:
        return []

    header_fields, header_line = records[0]
    header = []
    seen = set()
    for name in header_fields:
        name = name.strip()
        if name == "":
            raise CsvError("empty header name on line %d" % header_line, line=header_line)
        if name in seen:
            raise CsvError(
                "duplicate header name %r on line %d" % (name, header_line),
                line=header_line,
            )
        seen.add(name)
        header.append(name)

    rows = []
    for fields, line in records[1:]:
        if len(fields) > len(header):
            raise CsvError(
                "record on line %d has %d fields, header has %d"
                % (line, len(fields), len(header)),
                line=line,
            )
        padded = fields + [""] * (len(header) - len(fields))
        rows.append(dict(zip(header, padded)))
    return rows

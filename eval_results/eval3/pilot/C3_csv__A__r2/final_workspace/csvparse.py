"""Strict CSV parser. Standard library only; does not use the csv module."""


class CsvError(ValueError):
    """Malformed CSV input. ``line`` is the 1-based line number, or None."""

    def __init__(self, message, line=None):
        super().__init__(message)
        self.line = line


def _check_delimiter(delimiter):
    if not isinstance(delimiter, str) or len(delimiter) != 1 or delimiter in '"\r\n':
        raise ValueError(
            "delimiter must be a single character other than '\"', '\\r' or '\\n'"
        )


def _newline_at(text, i, line):
    """Consume the record separator starting at text[i]; return (new_i, new_line)."""
    if text[i] == "\r" and i + 1 < len(text) and text[i + 1] == "\n":
        return i + 2, line + 1
    return i + 1, line + 1


def _parse_records(text, delimiter):
    """Return a list of (start_line, fields) tuples, one per record."""
    _check_delimiter(delimiter)
    if text.startswith("﻿"):
        text = text[1:]
    n = len(text)
    i = 0
    line = 1
    records = []
    while i < n:
        if text[i] in "\r\n":
            # Completely empty line: skipped, produces no record.
            i, line = _newline_at(text, i, line)
            continue

        start_line = line
        fields = []
        while True:
            if i < n and text[i] == '"':
                open_line = line
                i += 1
                buf = []
                while True:
                    if i >= n:
                        raise CsvError("unterminated quoted field", open_line)
                    c = text[i]
                    if c == '"':
                        if i + 1 < n and text[i + 1] == '"':
                            buf.append('"')
                            i += 2
                        else:
                            i += 1
                            break
                    elif c in "\r\n":
                        j = i
                        i, line = _newline_at(text, i, line)
                        buf.append(text[j:i])
                    else:
                        buf.append(c)
                        i += 1
                fields.append("".join(buf))
                if i >= n:
                    break
                c = text[i]
                if c == delimiter:
                    i += 1
                    continue
                if c in "\r\n":
                    i, line = _newline_at(text, i, line)
                    break
                raise CsvError("unexpected character after closing quote", line)
            else:
                j = i
                while j < n and text[j] != delimiter and text[j] not in "\r\n":
                    j += 1
                fields.append(text[i:j])
                i = j
                if i >= n:
                    break
                if text[i] == delimiter:
                    i += 1
                    continue
                i, line = _newline_at(text, i, line)
                break
        records.append((start_line, fields))
    return records


def parse_csv(text, delimiter=","):
    """Parse a CSV document into a list of records (lists of strings)."""
    return [fields for _, fields in _parse_records(text, delimiter)]


def parse_csv_dicts(text, delimiter=","):
    """Parse CSV using the first record as the header; return one dict per row."""
    records = _parse_records(text, delimiter)
    if not records:
        return []

    header_line, raw_header = records[0]
    header = [name.strip() for name in raw_header]
    seen = set()
    for name in header:
        if name == "":
            raise CsvError("empty header name", header_line)
        if name in seen:
            raise CsvError("duplicate header name %r" % name, header_line)
        seen.add(name)

    width = len(header)
    result = []
    for line_no, fields in records[1:]:
        if len(fields) > width:
            raise CsvError(
                "record has %d fields, header has %d" % (len(fields), width),
                line_no,
            )
        if len(fields) < width:
            fields = fields + [""] * (width - len(fields))
        result.append(dict(zip(header, fields)))
    return result

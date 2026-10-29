"""Minimal CSV parser (no use of the csv module)."""


def _is_terminator_at(text, i):
    """Return the length of a record terminator starting at i, or 0."""
    if i < len(text):
        if text[i] == "\n":
            return 1
        if text[i] == "\r" and i + 1 < len(text) and text[i + 1] == "\n":
            return 2
    return 0


def parse_csv(text):
    """Parse CSV text into a list of records, each a list of string fields."""
    if not text:
        return []

    n = len(text)
    records = []
    record = []
    i = 0

    while True:
        # Parse one field starting at i.
        if i < n and text[i] == '"':
            i += 1
            buf = []
            while True:
                if i >= n:
                    raise ValueError("unterminated quoted field")
                c = text[i]
                if c == '"':
                    if i + 1 < n and text[i + 1] == '"':
                        buf.append('"')
                        i += 2
                        continue
                    i += 1  # closing quote
                    break
                buf.append(c)
                i += 1
            field = "".join(buf)
            if i < n and text[i] != "," and not _is_terminator_at(text, i):
                raise ValueError("unexpected character after closing quote")
        else:
            start = i
            while i < n and text[i] != "," and not _is_terminator_at(text, i):
                i += 1
            field = text[start:i]

        record.append(field)

        if i >= n:
            records.append(record)
            break

        if text[i] == ",":
            i += 1
            continue

        # Record terminator.
        i += _is_terminator_at(text, i)
        records.append(record)
        record = []
        if i >= n:
            break

    return records

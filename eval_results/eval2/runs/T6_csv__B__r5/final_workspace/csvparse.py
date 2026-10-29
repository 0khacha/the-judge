"""Minimal CSV parser (no use of the csv module)."""


def _is_terminator_at(text: str, i: int) -> bool:
    """True if a record terminator (\\n or \\r\\n) starts at index i."""
    if i >= len(text):
        return False
    if text[i] == "\n":
        return True
    return text[i] == "\r" and i + 1 < len(text) and text[i + 1] == "\n"


def parse_csv(text: str) -> list[list[str]]:
    """Parse CSV text into a list of records, each a list of string fields.

    Raises ValueError for an unterminated quoted field or for text between
    a closing quote and the next separator or terminator.
    """
    if text == "":
        return []

    records: list[list[str]] = []
    row: list[str] = []
    n = len(text)
    i = 0

    while True:
        # Parse one field starting at i.
        if i < n and text[i] == '"':
            i += 1
            buf: list[str] = []
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
                raise ValueError(f"unexpected character after closing quote at index {i}")
        else:
            start = i
            while i < n and text[i] != "," and not _is_terminator_at(text, i):
                i += 1
            field = text[start:i]

        row.append(field)

        if i >= n:
            records.append(row)
            break
        if text[i] == ",":
            i += 1
            continue

        # Record terminator.
        i += 2 if text[i] == "\r" else 1
        records.append(row)
        row = []
        if i >= n:
            break

    return records

"""A small CSV parser that does not use the csv module."""


def _at_terminator(text: str, i: int) -> bool:
    """Return True if a record terminator (\\n or \\r\\n) starts at index i."""
    return text.startswith("\n", i) or text.startswith("\r\n", i)


def parse_csv(text: str) -> list[list[str]]:
    """Parse CSV text into a list of records, each a list of string fields."""
    if text == "":
        return []

    records: list[list[str]] = []
    record: list[str] = []
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
            if not (i >= n or text[i] == "," or _at_terminator(text, i)):
                raise ValueError(f"unexpected character after closing quote at index {i}")
            record.append("".join(buf))
        else:
            start = i
            while i < n and text[i] != "," and not _at_terminator(text, i):
                i += 1
            record.append(text[start:i])

        # Decide what follows the field.
        if i >= n:
            records.append(record)
            break
        if text[i] == ",":
            i += 1  # next field in the same record (may be an empty trailing field)
            continue

        # Record terminator.
        records.append(record)
        record = []
        i += 2 if text.startswith("\r\n", i) else 1
        if i >= n:
            break  # a final terminator does not start an extra record

    return records

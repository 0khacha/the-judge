"""Minimal CSV parser (no use of the csv module)."""


def _at_terminator(text: str, i: int) -> bool:
    return text[i] == "\n" or text.startswith("\r\n", i)


def _parse_field(text: str, i: int) -> tuple[str, int]:
    """Parse one field starting at index i. Returns (value, next_index)."""
    n = len(text)
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
        if i < n and text[i] != "," and not _at_terminator(text, i):
            raise ValueError(f"unexpected character after closing quote at index {i}")
        return "".join(buf), i

    start = i
    while i < n and text[i] != "," and not _at_terminator(text, i):
        i += 1
    return text[start:i], i


def parse_csv(text: str) -> list[list[str]]:
    """Parse CSV text into a list of records, each a list of string fields."""
    n = len(text)
    if n == 0:
        return []

    records: list[list[str]] = []
    i = 0
    while True:
        record: list[str] = []
        while True:
            field, i = _parse_field(text, i)
            record.append(field)
            if i >= n:
                records.append(record)
                return records
            if text[i] == ",":
                i += 1
                continue
            # Record terminator: "\n" or "\r\n".
            i += 2 if text.startswith("\r\n", i) else 1
            records.append(record)
            if i >= n:
                return records
            break

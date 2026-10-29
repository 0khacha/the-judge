"""Minimal CSV parser (does not use the csv module).

Rules:
- ',' separates fields; records end at '\\n' or '\\r\\n' (never part of a field).
- A field starting with '"' is quoted: it runs to the closing '"'. Inside, '""'
  is a literal quote; commas and newlines are kept verbatim.
- After a closing quote the next character must be ',', a record terminator or
  end of input; an unterminated quote is an error.
- A '"' inside an unquoted field is literal. Whitespace is preserved.
- A final record terminator does not create an extra record.
"""


def _is_terminator(text: str, i: int) -> bool:
    """True if a record terminator ('\\n' or '\\r\\n') starts at index i."""
    if text[i] == "\n":
        return True
    return text[i] == "\r" and i + 1 < len(text) and text[i + 1] == "\n"


def _parse_quoted(text: str, i: int) -> tuple[str, int]:
    """Parse a quoted field whose opening quote is at index i.

    Returns the decoded field and the index just past the closing quote.
    """
    n = len(text)
    i += 1  # skip opening quote
    buf: list[str] = []
    while True:
        if i >= n:
            raise ValueError("unterminated quoted field")
        ch = text[i]
        if ch == '"':
            if i + 1 < n and text[i + 1] == '"':
                buf.append('"')
                i += 2
                continue
            return "".join(buf), i + 1
        buf.append(ch)
        i += 1


def _parse_unquoted(text: str, i: int) -> tuple[str, int]:
    """Parse an unquoted field starting at index i (may be empty)."""
    n = len(text)
    start = i
    while i < n and text[i] != "," and not _is_terminator(text, i):
        i += 1
    return text[start:i], i


def parse_csv(text: str) -> list[list[str]]:
    """Parse CSV text into a list of records, each a list of string fields."""
    if text == "":
        return []

    n = len(text)
    records: list[list[str]] = []
    i = 0
    while True:
        # Parse one record: fields separated by ',' until a terminator or end.
        fields: list[str] = []
        while True:
            if i < n and text[i] == '"':
                field, i = _parse_quoted(text, i)
                if i < n and text[i] != "," and not _is_terminator(text, i):
                    raise ValueError(
                        f"unexpected character {text[i]!r} after closing quote"
                    )
            else:
                field, i = _parse_unquoted(text, i)
            fields.append(field)

            if i >= n:
                records.append(fields)
                return records
            if text[i] == ",":
                i += 1
                continue
            # Must be a record terminator here.
            i += 2 if text[i] == "\r" else 1
            records.append(fields)
            break

        if i >= n:
            # Final terminator consumed; it does not start a new record.
            return records

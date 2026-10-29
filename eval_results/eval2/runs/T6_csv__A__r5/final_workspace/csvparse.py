"""Minimal CSV parser (no use of the csv module)."""


def _is_terminator(text: str, i: int) -> bool:
    """True if a record terminator (\\n or \\r\\n) starts at index i."""
    if i >= len(text):
        return False
    if text[i] == "\n":
        return True
    return text[i] == "\r" and i + 1 < len(text) and text[i + 1] == "\n"


def parse_csv(text: str) -> list[list[str]]:
    records: list[list[str]] = []
    n = len(text)
    i = 0
    while i < n:
        fields: list[str] = []
        while True:
            if i < n and text[i] == '"':
                # Quoted field: runs to the closing quote; "" is a literal quote.
                i += 1
                buf: list[str] = []
                closed = False
                while i < n:
                    ch = text[i]
                    if ch == '"':
                        if i + 1 < n and text[i + 1] == '"':
                            buf.append('"')
                            i += 2
                            continue
                        closed = True
                        i += 1
                        break
                    buf.append(ch)
                    i += 1
                if not closed:
                    raise ValueError("unterminated quoted field")
                fields.append("".join(buf))
                if i < n and text[i] != "," and not _is_terminator(text, i):
                    raise ValueError(
                        f"unexpected character {text[i]!r} after closing quote"
                    )
            else:
                # Unquoted field: runs to ',' or a record terminator.
                start = i
                while i < n and text[i] != "," and not _is_terminator(text, i):
                    i += 1
                fields.append(text[start:i])

            if i >= n:
                records.append(fields)
                return records
            if text[i] == ",":
                i += 1
                if i >= n:
                    # Trailing comma at end of input: trailing empty field.
                    fields.append("")
                    records.append(fields)
                    return records
                continue
            # Record terminator.
            i += 2 if text[i] == "\r" else 1
            records.append(fields)
            break

    return records

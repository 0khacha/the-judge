"""Minimal CSV parser (does not use the csv module)."""


def _at_terminator(text, i):
    """Return the length of a record terminator starting at i (0 if none)."""
    n = len(text)
    if i < n and text[i] == "\n":
        return 1
    if i + 1 < n and text[i] == "\r" and text[i + 1] == "\n":
        return 2
    return 0


def parse_csv(text):
    """Parse CSV text into a list of records, each a list of string fields."""
    records = []
    n = len(text)
    if n == 0:
        return records

    i = 0
    while True:
        record = []
        # Parse fields until the record ends.
        while True:
            if i < n and text[i] == '"':
                # Quoted field.
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
                record.append("".join(buf))
                # After the closing quote only ',', a terminator or end is allowed.
                if i < n and text[i] != "," and not _at_terminator(text, i):
                    raise ValueError(
                        f"unexpected character {text[i]!r} after closing quote"
                    )
            else:
                # Unquoted field: runs until ',' or a record terminator.
                start = i
                while i < n and text[i] != "," and not _at_terminator(text, i):
                    i += 1
                record.append(text[start:i])

            if i >= n:
                records.append(record)
                return records
            if text[i] == ",":
                i += 1
                continue
            # Record terminator.
            i += _at_terminator(text, i)
            records.append(record)
            break

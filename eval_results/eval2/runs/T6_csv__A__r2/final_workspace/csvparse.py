def _at_crlf(text, i):
    return text.startswith("\r\n", i)


def _at_terminator(text, i):
    return i < len(text) and (text[i] == "\n" or _at_crlf(text, i))


def parse_csv(text):
    """Parse CSV text into a list of records, each a list of string fields.

    Hand-written parser; does not use the csv module.
    """
    if text == "":
        return []

    n = len(text)
    records = []
    row = []
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
            if i < n and text[i] != "," and not _at_terminator(text, i):
                raise ValueError(f"unexpected character after closing quote at index {i}")
        else:
            start = i
            while i < n and text[i] != "," and not _at_terminator(text, i):
                i += 1
            field = text[start:i]

        row.append(field)

        if i >= n:
            records.append(row)
            break

        if text[i] == ",":
            i += 1
            continue

        # Record terminator: "\n" or "\r\n".
        i += 2 if text[i] == "\r" else 1
        records.append(row)
        row = []
        if i >= n:
            break

    return records

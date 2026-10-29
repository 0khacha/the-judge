"""A small CSV parser that does not use the csv module."""


def parse_csv(text: str) -> list[list[str]]:
    """Parse CSV text into a list of records, each a list of string fields.

    Fields are separated by ','. Records end at '\\n' or '\\r\\n'. A field
    starting with '"' is quoted: '""' inside it is a literal quote, and
    separators and newlines are kept as content. Raises ValueError on an
    unterminated quote or on a character following a closing quote that is
    neither a separator, a record terminator, nor end of input.
    """
    records: list[list[str]] = []
    n = len(text)
    i = 0

    if n == 0:
        return records

    while True:
        # Start of a record: parse fields until a record terminator or end.
        fields: list[str] = []
        while True:
            # Start of a field.
            if i < n and text[i] == '"':
                # Quoted field.
                i += 1
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
                        # Closing quote.
                        i += 1
                        break
                    buf.append(ch)
                    i += 1
                fields.append("".join(buf))
                # After a closing quote: separator, terminator, or end only.
                if i < n and text[i] not in ",\r\n":
                    raise ValueError(
                        f"unexpected character {text[i]!r} after closing quote"
                    )
            else:
                # Unquoted field: runs to the next ',' or terminator.
                start = i
                while i < n and text[i] not in ",\r\n":
                    i += 1
                fields.append(text[start:i])

            # What ends this field?
            if i >= n:
                records.append(fields)
                return records
            ch = text[i]
            if ch == ",":
                i += 1
                continue  # next field in the same record (may be empty at end)
            # Record terminator: '\r\n' or '\n' (a lone '\r' is treated as one).
            if ch == "\r" and i + 1 < n and text[i + 1] == "\n":
                i += 2
            else:
                i += 1
            records.append(fields)
            break

        if i >= n:
            return records

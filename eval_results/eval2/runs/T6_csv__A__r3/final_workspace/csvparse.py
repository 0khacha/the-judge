def parse_csv(text):
    """Parse CSV text into a list of records, each a list of string fields.

    Implemented without the csv module. Records end at "\\n" or "\\r\\n";
    a quoted field may contain commas, newlines and "" escapes.
    """
    if not text:
        return []

    n = len(text)

    def is_term(pos):
        if text[pos] == "\n":
            return True
        return text[pos] == "\r" and pos + 1 < n and text[pos + 1] == "\n"

    records = []
    i = 0
    while True:
        row = []
        while True:
            if i < n and text[i] == '"':
                # Quoted field: runs to the closing quote; "" is a literal quote.
                i += 1
                buf = []
                while True:
                    if i >= n:
                        raise ValueError("unterminated quoted field")
                    if text[i] == '"':
                        if i + 1 < n and text[i + 1] == '"':
                            buf.append('"')
                            i += 2
                            continue
                        i += 1
                        break
                    buf.append(text[i])
                    i += 1
                row.append("".join(buf))
                if i < n and text[i] != "," and not is_term(i):
                    raise ValueError(
                        "unexpected character after closing quote at index %d" % i
                    )
            else:
                # Unquoted field: literal text up to ',' or a record terminator.
                start = i
                while i < n and text[i] != "," and not is_term(i):
                    i += 1
                row.append(text[start:i])

            if i < n and text[i] == ",":
                i += 1
                continue
            break

        records.append(row)
        if i >= n:
            return records
        # Consume the record terminator ("\r\n" or "\n").
        i += 2 if text[i] == "\r" else 1
        if i >= n:
            # A final terminator does not start an extra record.
            return records

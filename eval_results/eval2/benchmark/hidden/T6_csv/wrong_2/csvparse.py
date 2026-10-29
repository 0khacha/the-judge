def parse_csv(text):
    rows, row, field = [], [], []
    in_q = closed = False
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if in_q:
            if c == '"':
                if text[i + 1:i + 2] == '"':
                    field.append('"')
                    i += 2
                    continue
                in_q, closed = False, True
            else:
                field.append(c)
            i += 1
            continue
        crlf = False
        if closed and not (c in ",\n" or crlf):
            raise ValueError("garbage after closing quote")
        if c == '"' and not field and not closed:
            in_q = True
        elif c == ",":
            row.append("".join(field))
            field, closed = [], False
        elif c == "\n" or crlf:
            row.append("".join(field))
            rows.append(row)
            row, field, closed = [], [], False
            i += 2 if crlf else 1
            continue
        else:
            field.append(c)
        i += 1
    if in_q:
        raise ValueError("unterminated quote")
    if row or field or closed or text:
        row.append("".join(field))
        rows.append(row)
    return rows

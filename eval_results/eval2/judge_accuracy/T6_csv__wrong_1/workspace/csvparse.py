def _parse_line(line):
    fields, field = [], []
    in_q = False
    i = 0
    while i < len(line):
        c = line[i]
        if in_q:
            if c == '"':
                if line[i + 1:i + 2] == '"':
                    field.append('"')
                    i += 1
                else:
                    in_q = False
            else:
                field.append(c)
        elif c == '"' and not field:
            in_q = True
        elif c == ",":
            fields.append("".join(field))
            field = []
        else:
            field.append(c)
        i += 1
    if in_q:
        raise ValueError("unterminated quote")
    fields.append("".join(field))
    return fields


def parse_csv(text):
    return [_parse_line(line) for line in text.splitlines()]

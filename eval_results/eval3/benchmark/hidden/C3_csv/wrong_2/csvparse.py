class CsvError(ValueError):
    def __init__(self, message, line=None):
        super().__init__("line %s: %s" % (line, message) if line is not None else message)
        self.line = line


def parse_csv(text, delimiter=","):
    if not isinstance(delimiter, str) or len(delimiter) != 1 or delimiter in '"\r\n':
        raise ValueError("invalid delimiter")
    if text.startswith("\ufeff"):
        text = text[1:]
    records = []
    i = 0
    n = len(text)
    line = 1
    while i < n:
        if text[i] in "\r\n":
            if text[i] == "\r" and i + 1 < n and text[i + 1] == "\n":
                i += 2
            else:
                i += 1
            line += 1
            continue
        fields = []
        while True:
            if i < n and text[i] == '"':
                start_line = line
                i += 1
                buf = []
                while True:
                    if i >= n:
                        raise CsvError("unterminated quoted field", start_line)
                    c = text[i]
                    if c == '"':
                        if i + 1 < n and text[i + 1] == '"':
                            buf.append('"')
                            i += 2
                            continue
                        i += 1
                        break
                    if c == "\r":
                        if i + 1 < n and text[i + 1] == "\n":
                            buf.append("\r\n")
                            i += 2
                        else:
                            buf.append("\r")
                            i += 1
                        line += 1
                    elif c == "\n":
                        buf.append("\n")
                        i += 1
                        line += 1
                    else:
                        buf.append(c)
                        i += 1
                value = "".join(buf)
                if i < n and text[i] == delimiter:
                    fields.append(value)
                    i += 1
                    continue
                if i >= n or text[i] in "\r\n":
                    fields.append(value)
                    break
                raise CsvError("unexpected character after closing quote", line)
            j = i
            while j < n and text[j] != delimiter and text[j] not in "\r\n":
                j += 1
            fields.append(text[i:j].strip())
            i = j
            if i < n and text[i] == delimiter:
                i += 1
                continue
            break
        records.append(fields)
        if i < n:
            if text[i] == "\r" and i + 1 < n and text[i + 1] == "\n":
                i += 2
            else:
                i += 1
            line += 1
    return records


def parse_csv_dicts(text, delimiter=","):
    records = parse_csv(text, delimiter)
    if not records:
        return []
    header = [h.strip() for h in records[0]]
    if any(h == "" for h in header):
        raise CsvError("empty column name")
    out = []
    for rec in records[1:]:
        if len(rec) > len(header):
            raise CsvError("too many fields")
        rec = rec + [""] * (len(header) - len(rec))
        out.append(dict(zip(header, rec)))
    return out

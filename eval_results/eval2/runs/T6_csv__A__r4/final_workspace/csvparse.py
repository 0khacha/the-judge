"""Minimal CSV parser without the csv module."""


def parse_csv(text: str) -> list[list[str]]:
    records: list[list[str]] = []
    n = len(text)
    if n == 0:
        return records

    i = 0
    while True:
        # Parse one record starting at i.
        fields: list[str] = []
        while True:
            # Parse one field starting at i.
            if i < n and text[i] == '"':
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
                        i += 1  # closing quote
                        break
                    buf.append(ch)
                    i += 1
                fields.append("".join(buf))
                # After closing quote: must be ',', terminator, or end of input.
                if i < n and text[i] not in (",", "\n", "\r"):
                    raise ValueError(f"unexpected character after closing quote at index {i}")
            else:
                start = i
                while i < n and text[i] not in (",", "\n", "\r"):
                    i += 1
                fields.append(text[start:i])

            # Decide what follows the field.
            if i >= n:
                records.append(fields)
                return records
            ch = text[i]
            if ch == ",":
                i += 1
                # Trailing comma at end of input yields a trailing empty field.
                if i >= n:
                    fields.append("")
                    records.append(fields)
                    return records
                continue
            # Record terminator: \n or \r\n (a lone \r also terminates).
            if ch == "\r" and i + 1 < n and text[i + 1] == "\n":
                i += 2
            else:
                i += 1
            records.append(fields)
            if i >= n:
                return records
            break

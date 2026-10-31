import re

_ESC = re.compile(r"(?:%[0-9A-Fa-f]{2})+")


def _decode(s: str) -> str:
    s = s.replace("+", " ")

    def repl(m):
        raw = bytes.fromhex(m.group(0).replace("%", ""))
        # decode as UTF-8; keep invalid bytes literally
        out = []
        i = 0
        text = m.group(0)
        while i < len(raw):
            for n in (4, 3, 2, 1):
                chunk = raw[i:i + n]
                if len(chunk) != n:
                    continue
                try:
                    out.append(chunk.decode("utf-8"))
                    i += n
                    break
                except UnicodeDecodeError:
                    continue
            else:
                out.append(text[i * 3:i * 3 + 3])
                i += 1
        return "".join(out)

    return _ESC.sub(repl, s)


def parse_query(qs: str) -> dict:
    if qs.startswith("?"):
        qs = qs[1:]
    result: dict = {}
    for seg in qs.split("&"):
        if not seg:
            continue
        key, sep, val = seg.partition("=")
        result.setdefault(_decode(key), []).append(_decode(val))
    return result

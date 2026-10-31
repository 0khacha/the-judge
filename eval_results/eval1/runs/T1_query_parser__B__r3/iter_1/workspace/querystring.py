import re

_HEX2 = re.compile(r"[0-9A-Fa-f]{2}")


def _decode(s: str) -> str:
    s = s.replace("+", " ")
    if "%" not in s:
        return s
    out = bytearray()
    i = 0
    while i < len(s):
        c = s[i]
        if c == "%" and _HEX2.fullmatch(s[i + 1:i + 3]):
            out.append(int(s[i + 1:i + 3], 16))
            i += 3
        else:
            out.extend(c.encode("utf-8", "surrogatepass"))
            i += 1
    return out.decode("utf-8", errors="replace")


def parse_query(qs: str) -> dict:
    if qs.startswith("?"):
        qs = qs[1:]
    result: dict = {}
    for seg in qs.split("&"):
        if not seg:
            continue
        key, _, val = seg.partition("=")
        result.setdefault(_decode(key), []).append(_decode(val))
    return result

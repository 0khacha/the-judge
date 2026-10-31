from urllib.parse import unquote


def _decode(s):
    return unquote(s.replace("+", " "), encoding="utf-8", errors="strict")


def parse_query(qs: str) -> dict:
    if qs.startswith("?"):
        qs = qs[1:]
    out = {}
    for seg in qs.split("&"):
        if not seg:
            continue
        key, _, value = seg.partition("=")
        out.setdefault(_decode(key), []).append(_decode(value))
    return out

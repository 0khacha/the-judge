import re

_ESC = re.compile(r"(?:%[0-9A-Fa-f]{2})+")


def _decode(s: str) -> str:
    s = s.replace("+", " ")

    def repl(m):
        raw = bytes.fromhex(m.group(0).replace("%", ""))
        return raw.decode("utf-8", errors="replace")

    return _ESC.sub(repl, s)


def parse_query(qs: str) -> dict[str, list[str]]:
    if qs.startswith("?"):
        qs = qs[1:]
    result: dict[str, list[str]] = {}
    for seg in qs.split("&"):
        if not seg:
            continue
        key, _, value = seg.partition("=")
        result.setdefault(_decode(key), []).append(_decode(value))
    return result

import re

_RUN = re.compile(r"(?:%[0-9A-Fa-f]{2})+")


def _run_repl(m):
    raw = m.group(0)
    try:
        return bytes.fromhex(raw.replace("%", "")).decode("utf-8")
    except UnicodeDecodeError:
        return raw


def _decode(s: str) -> str:
    return _RUN.sub(_run_repl, s.replace("+", " "))


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

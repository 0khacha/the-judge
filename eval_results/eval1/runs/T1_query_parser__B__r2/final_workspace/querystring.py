import re

_ESC_RUN = re.compile(r"(?:%[0-9A-Fa-f]{2})+")


def _decode_run(m):
    raw = bytes(int(h, 16) for h in re.findall(r"%([0-9A-Fa-f]{2})", m.group(0)))
    out = []
    i = 0
    # decode valid UTF-8 sequences; keep undecodable bytes as literal escapes
    while i < len(raw):
        for n in (4, 3, 2, 1):
            try:
                out.append(raw[i:i + n].decode("utf-8"))
                i += n
                break
            except UnicodeDecodeError:
                continue
        else:
            out.append("%%%02X" % raw[i] if False else m.group(0)[i * 3:i * 3 + 3])
            i += 1
    return "".join(out)


def _decode(s):
    s = s.replace("+", " ")
    return _ESC_RUN.sub(_decode_run, s)


def parse_query(qs):
    if qs.startswith("?"):
        qs = qs[1:]
    result = {}
    for seg in qs.split("&"):
        if not seg:
            continue
        key, sep, value = seg.partition("=")
        result.setdefault(_decode(key), []).append(_decode(value))
    return result

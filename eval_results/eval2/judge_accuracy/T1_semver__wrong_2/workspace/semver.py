def _parse(v):
    if not isinstance(v, str):
        raise ValueError("not a string")
    build = ""
    if "+" in v:
        v, build = v.split("+", 1)
    core, sep, pre = v.partition("-")
    parts = core.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(v)
    ids = pre.split(".") if sep else []
    if any(i == "" for i in ids):
        raise ValueError(v)
    return tuple(int(p) for p in parts), ids, build


def _key(i):
    return (0, int(i), "") if i.isdigit() else (1, 0, i)


def compare(a, b):
    ca, pa, ba = _parse(a)
    cb, pb, bb = _parse(b)
    if ca != cb:
        return -1 if ca < cb else 1
    if pa != pb:
        if not pa:
            return 1
        if not pb:
            return -1
        ka, kb = [_key(i) for i in pa], [_key(i) for i in pb]
        return -1 if ka < kb else 1
    return (ba > bb) - (ba < bb)


def sort_versions(versions):
    import functools
    return sorted(versions, key=functools.cmp_to_key(compare))

def _parse(v):
    if not isinstance(v, str):
        raise ValueError("not a string")
    main = v.split("+", 1)[0]
    core, sep, pre = main.partition("-")
    parts = core.split(".")
    if len(parts) != 3 or not all(p.isascii() and p.isdigit() for p in parts):
        raise ValueError(v)
    ids = []
    if sep:
        ids = pre.split(".")
        if any(i == "" for i in ids):
            raise ValueError(v)
    return tuple(int(p) for p in parts), ids


def _cmp_id(a, b):
    an, bn = a.isascii() and a.isdigit(), b.isascii() and b.isdigit()
    if an and bn:
        a, b = int(a), int(b)
    elif an:
        return -1
    elif bn:
        return 1
    return (a > b) - (a < b)


def compare(a, b):
    ca, pa = _parse(a)
    cb, pb = _parse(b)
    if ca != cb:
        return -1 if ca < cb else 1
    if not pa and not pb:
        return 0
    if not pa:
        return 1
    if not pb:
        return -1
    for x, y in zip(pa, pb):
        c = _cmp_id(x, y)
        if c:
            return c
    return (len(pa) > len(pb)) - (len(pa) < len(pb))


def sort_versions(versions):
    import functools
    return sorted(versions, key=functools.cmp_to_key(compare))

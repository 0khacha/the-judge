def _parse(v):
    if not isinstance(v, str):
        raise ValueError("not a string")
    main = v.split("+", 1)[0]
    core, sep, pre = main.partition("-")
    parts = core.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(v)
    if sep and pre == "":
        raise ValueError(v)
    return tuple(int(p) for p in parts), (pre if sep else None)


def compare(a, b):
    ca, pa = _parse(a)
    cb, pb = _parse(b)
    if ca != cb:
        return -1 if ca < cb else 1
    if pa == pb:
        return 0
    if pa is None:
        return 1
    if pb is None:
        return -1
    return -1 if pa < pb else 1


def sort_versions(versions):
    import functools
    return sorted(versions, key=functools.cmp_to_key(compare))

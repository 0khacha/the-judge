"""Semantic version comparison following semver 2.0.0 precedence rules."""

import re

_CORE_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_NUMERIC_RE = re.compile(r"^\d+$")


def _parse(version):
    if not isinstance(version, str):
        raise ValueError("version must be a string")

    build_split = version.split("+", 1)
    main = build_split[0]

    pre_split = main.split("-", 1)
    core = pre_split[0]
    prerelease = pre_split[1] if len(pre_split) == 2 else None

    match = _CORE_RE.match(core)
    if not match:
        raise ValueError(f"invalid version core: {version!r}")
    numbers = tuple(int(part) for part in match.groups())

    prerelease_ids = None
    if prerelease is not None:
        prerelease_ids = prerelease.split(".")
        for ident in prerelease_ids:
            if ident == "":
                raise ValueError(f"empty prerelease identifier: {version!r}")

    return numbers, prerelease_ids


def _compare_identifier(x, y):
    x_num = bool(_NUMERIC_RE.match(x))
    y_num = bool(_NUMERIC_RE.match(y))
    if x_num and y_num:
        xi, yi = int(x), int(y)
        return (xi > yi) - (xi < yi)
    if x_num != y_num:
        # numeric identifiers have lower precedence than non-numeric
        return -1 if x_num else 1
    return (x > y) - (x < y)


def _compare_prerelease(a_ids, b_ids):
    # Both None or equal-precedence handled by caller.
    for x, y in zip(a_ids, b_ids):
        result = _compare_identifier(x, y)
        if result != 0:
            return result
    return (len(a_ids) > len(b_ids)) - (len(a_ids) < len(b_ids))


def compare(a, b):
    """Return -1, 0 or 1 comparing semver strings a and b (build metadata ignored)."""
    a_core, a_pre = _parse(a)
    b_core, b_pre = _parse(b)

    if a_core != b_core:
        return -1 if a_core < b_core else 1

    if a_pre is None and b_pre is None:
        return 0
    if a_pre is None:
        return 1  # release is higher than prerelease
    if b_pre is None:
        return -1

    return _compare_prerelease(a_pre, b_pre)


def sort_versions(versions):
    """Return a new list of versions sorted ascending by precedence (stable)."""
    import functools

    return sorted(versions, key=functools.cmp_to_key(compare))

"""Semantic version (semver 2.0.0) comparison utilities."""

import re

_CORE_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_NUMERIC_RE = re.compile(r"^\d+$")


def _parse(version):
    if not isinstance(version, str):
        raise ValueError(f"version must be a string, got {type(version).__name__}")

    rest, sep, _build = version.partition("+")
    if sep and not _build:
        raise ValueError(f"empty build metadata in {version!r}")

    core, dash, pre = rest.partition("-")
    m = _CORE_RE.match(core)
    if not m:
        raise ValueError(f"invalid version core in {version!r}")

    major, minor, patch = (int(g) for g in m.groups())

    prerelease = None
    if dash:
        identifiers = pre.split(".")
        for ident in identifiers:
            if ident == "":
                raise ValueError(f"empty prerelease identifier in {version!r}")
            if not re.fullmatch(r"[0-9A-Za-z-]+", ident):
                raise ValueError(f"invalid prerelease identifier in {version!r}")
        prerelease = identifiers

    return (major, minor, patch), prerelease


def _compare_identifier(x, y):
    x_num = bool(_NUMERIC_RE.match(x))
    y_num = bool(_NUMERIC_RE.match(y))
    if x_num and y_num:
        xi, yi = int(x), int(y)
        return (xi > yi) - (xi < yi)
    if x_num:
        return -1
    if y_num:
        return 1
    return (x > y) - (x < y)


def _compare_prerelease(a, b):
    # Both None: equal. Version without prerelease has higher precedence.
    if a is None and b is None:
        return 0
    if a is None:
        return 1
    if b is None:
        return -1

    for x, y in zip(a, b):
        c = _compare_identifier(x, y)
        if c:
            return c
    return (len(a) > len(b)) - (len(a) < len(b))


def compare(a, b):
    """Return -1, 0 or 1 comparing semver strings a and b by precedence."""
    core_a, pre_a = _parse(a)
    core_b, pre_b = _parse(b)
    if core_a != core_b:
        return -1 if core_a < core_b else 1
    return _compare_prerelease(pre_a, pre_b)


def sort_versions(versions):
    """Return a new list of versions sorted ascending by precedence (stable)."""
    from functools import cmp_to_key

    return sorted(versions, key=cmp_to_key(compare))

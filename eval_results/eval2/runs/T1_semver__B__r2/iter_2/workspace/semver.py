"""Semantic version (semver 2.0.0) comparison and sorting."""

import functools
import re

_CORE_RE = re.compile(r"[0-9]+")
_IDENT_RE = re.compile(r"[0-9A-Za-z-]+")


def _parse(version):
    """Split a version string into (core ints, prerelease identifiers).

    Build metadata is validated and discarded.
    Raises ValueError on invalid input.
    """
    if not isinstance(version, str):
        raise ValueError(f"version must be a str, got {type(version).__name__}")

    rest = version
    if "+" in rest:
        rest, build = rest.split("+", 1)
        build_idents = build.split(".")
        if not all(_IDENT_RE.fullmatch(i) for i in build_idents):
            raise ValueError(f"invalid build metadata in {version!r}")

    prerelease = None
    if "-" in rest:
        rest, prerelease = rest.split("-", 1)

    core_parts = rest.split(".")
    if len(core_parts) != 3 or not all(_CORE_RE.fullmatch(p) for p in core_parts):
        raise ValueError(f"invalid version core in {version!r}")
    core = tuple(int(p) for p in core_parts)

    pre_idents = None
    if prerelease is not None:
        pre_idents = prerelease.split(".")
        if not all(_IDENT_RE.fullmatch(i) for i in pre_idents):
            raise ValueError(f"invalid prerelease in {version!r}")

    return core, pre_idents


def _compare_identifier(x, y):
    x_num = x.isdigit()
    y_num = y.isdigit()
    if x_num and y_num:
        xi, yi = int(x), int(y)
        return (xi > yi) - (xi < yi)
    if x_num != y_num:
        # numeric identifiers have lower precedence than alphanumeric ones
        return -1 if x_num else 1
    return (x > y) - (x < y)


def _compare_prerelease(a, b):
    if a is None and b is None:
        return 0
    # A version without prerelease has higher precedence.
    if a is None:
        return 1
    if b is None:
        return -1
    for x, y in zip(a, b):
        c = _compare_identifier(x, y)
        if c:
            return c
    return (len(a) > len(b)) - (len(a) < len(b))


def _cmp(a, b):
    core_a, pre_a = _parse(a)
    core_b, pre_b = _parse(b)
    if core_a != core_b:
        return -1 if core_a < core_b else 1
    return _compare_prerelease(pre_a, pre_b)


def compare(a, b):
    """Return -1, 0 or 1 according to semver precedence of a versus b."""
    return _cmp(a, b)


def sort_versions(versions):
    """Return a new list of versions sorted ascending by precedence (stable)."""
    versions = list(versions)
    for v in versions:
        _parse(v)  # validate everything up front
    return sorted(versions, key=functools.cmp_to_key(_cmp))

"""Semantic version comparison following semver 2.0.0 precedence rules."""

import re
from functools import cmp_to_key

_CORE_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_NUMERIC_RE = re.compile(r"^\d+$")


def _parse(version):
    if not isinstance(version, str):
        raise ValueError(f"version must be a string, got {type(version).__name__}")

    rest = version
    build = None
    if "+" in rest:
        rest, build = rest.split("+", 1)
        if build == "" or any(not ident or not re.fullmatch(r"[0-9A-Za-z-]+", ident)
                              for ident in build.split(".")):
            raise ValueError(f"invalid build metadata in {version!r}")

    prerelease = None
    if "-" in rest:
        core, prerelease = rest.split("-", 1)
    else:
        core = rest

    match = _CORE_RE.match(core)
    if not match:
        raise ValueError(f"invalid version core in {version!r}")
    major, minor, patch = (int(part) for part in match.groups())

    prerelease_ids = None
    if prerelease is not None:
        ids = prerelease.split(".")
        for ident in ids:
            if ident == "":
                raise ValueError(f"empty prerelease identifier in {version!r}")
            if not re.fullmatch(r"[0-9A-Za-z-]+", ident):
                raise ValueError(f"invalid prerelease identifier in {version!r}")
        prerelease_ids = ids

    return (major, minor, patch), prerelease_ids


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


def _compare_prerelease(a_ids, b_ids):
    # No prerelease ranks higher than any prerelease.
    if a_ids is None and b_ids is None:
        return 0
    if a_ids is None:
        return 1
    if b_ids is None:
        return -1
    for x, y in zip(a_ids, b_ids):
        result = _compare_identifier(x, y)
        if result:
            return result
    return (len(a_ids) > len(b_ids)) - (len(a_ids) < len(b_ids))


def compare(a, b):
    """Return -1, 0 or 1 according to semver precedence of a versus b."""
    a_core, a_pre = _parse(a)
    b_core, b_pre = _parse(b)
    if a_core != b_core:
        return -1 if a_core < b_core else 1
    return _compare_prerelease(a_pre, b_pre)


def sort_versions(versions):
    """Return a new list sorted ascending by precedence (stable)."""
    return sorted(versions, key=cmp_to_key(compare))

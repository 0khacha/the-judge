"""Semantic version (semver 2.0.0) precedence comparison."""

import functools
import re

_NUMERIC_ID = r"0|[1-9]\d*"
_ALNUM_ID = r"[0-9A-Za-z-]+"

_VERSION_RE = re.compile(
    r"(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<pre>" + _ALNUM_ID + r"(?:\." + _ALNUM_ID + r")*))?"
    r"(?:\+(?P<build>" + _ALNUM_ID + r"(?:\." + _ALNUM_ID + r")*))?"
)
_NUMERIC_RE = re.compile(_NUMERIC_ID)


def _parse(version):
    """Return (core tuple, prerelease identifiers tuple or ())."""
    if not isinstance(version, str):
        raise ValueError(f"version must be a string, got {type(version).__name__}")
    match = _VERSION_RE.fullmatch(version)
    if match is None:
        raise ValueError(f"invalid semantic version: {version!r}")
    core = (int(match["major"]), int(match["minor"]), int(match["patch"]))
    pre = match["pre"]
    identifiers = tuple(pre.split(".")) if pre else ()
    for ident in identifiers:
        # Numeric identifiers must not have leading zeros.
        if ident.isdigit() and not _NUMERIC_RE.fullmatch(ident):
            raise ValueError(f"invalid prerelease identifier in {version!r}: {ident!r}")
    return core, identifiers


def _compare_identifier(x, y):
    x_num = x.isdigit()
    y_num = y.isdigit()
    if x_num and y_num:
        xi, yi = int(x), int(y)
        return (xi > yi) - (xi < yi)
    if x_num != y_num:
        # Numeric identifiers have lower precedence than alphanumeric ones.
        return -1 if x_num else 1
    return (x > y) - (x < y)


def _compare_prerelease(a_ids, b_ids):
    if not a_ids and not b_ids:
        return 0
    # A version without prerelease has higher precedence.
    if not a_ids:
        return 1
    if not b_ids:
        return -1
    for x, y in zip(a_ids, b_ids):
        result = _compare_identifier(x, y)
        if result:
            return result
    return (len(a_ids) > len(b_ids)) - (len(a_ids) < len(b_ids))


def compare(a, b):
    """Compare two semantic versions. Returns -1, 0 or 1."""
    a_core, a_pre = _parse(a)
    b_core, b_pre = _parse(b)
    if a_core != b_core:
        return -1 if a_core < b_core else 1
    return _compare_prerelease(a_pre, b_pre)


def sort_versions(versions):
    """Return a new list of versions sorted ascending by precedence (stable)."""
    items = list(versions)
    for item in items:
        _parse(item)  # validate everything up front, even a lone element
    return sorted(items, key=functools.cmp_to_key(compare))

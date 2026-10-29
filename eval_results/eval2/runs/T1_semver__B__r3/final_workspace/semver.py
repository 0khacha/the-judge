"""Semantic version (semver 2.0.0) precedence comparison."""

import functools
import re

_CORE_RE = re.compile(r"([0-9]+)\.([0-9]+)\.([0-9]+)\Z")
_IDENT_RE = re.compile(r"[0-9A-Za-z-]+\Z")
_NUMERIC_RE = re.compile(r"[0-9]+\Z")


def _parse(version):
    if not isinstance(version, str):
        raise ValueError(f"version must be a string, got {type(version).__name__}")

    rest = version
    build = None
    if "+" in rest:
        rest, build = rest.split("+", 1)
        if not build or any(not _IDENT_RE.match(p) for p in build.split(".")):
            raise ValueError(f"invalid build metadata in {version!r}")

    prerelease = None
    if "-" in rest:
        rest, prerelease = rest.split("-", 1)
        if prerelease == "":
            raise ValueError(f"empty prerelease in {version!r}")
        idents = prerelease.split(".")
        for ident in idents:
            if ident == "":
                raise ValueError(f"empty prerelease identifier in {version!r}")
            if not _IDENT_RE.match(ident):
                raise ValueError(f"invalid prerelease identifier in {version!r}")

    m = _CORE_RE.match(rest)
    if not m:
        raise ValueError(f"invalid version core in {version!r}")

    core = tuple(int(part) for part in m.groups())
    if prerelease is None:
        pre_key = None
    else:
        pre_key = tuple(
            (0, int(ident), "") if _NUMERIC_RE.match(ident) else (1, 0, ident)
            for ident in prerelease.split(".")
        )
    return core, pre_key


def _cmp(x, y):
    return (x > y) - (x < y)


def compare(a, b):
    """Return -1, 0 or 1 comparing semver precedence of a and b.

    Build metadata is ignored. Raises ValueError on invalid input.
    """
    core_a, pre_a = _parse(a)
    core_b, pre_b = _parse(b)

    c = _cmp(core_a, core_b)
    if c:
        return c

    # A version without prerelease has higher precedence.
    if pre_a is None and pre_b is None:
        return 0
    if pre_a is None:
        return 1
    if pre_b is None:
        return -1

    # Tuple comparison handles the shorter-is-lower rule when prefixes match.
    return _cmp(pre_a, pre_b)


def sort_versions(versions):
    """Return a new list of versions sorted ascending by precedence (stable)."""
    return sorted(versions, key=functools.cmp_to_key(compare))

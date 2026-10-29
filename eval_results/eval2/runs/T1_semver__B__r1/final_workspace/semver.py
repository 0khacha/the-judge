"""Semantic version (semver 2.0.0) comparison and sorting."""

import re

_CORE_RE = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
_IDENT_RE = re.compile(r"[0-9A-Za-z-]+")


def _ident_key(ident):
    # Numeric identifiers sort below alphanumeric ones; numeric compare as ints,
    # alphanumeric compare lexically (ASCII).
    if ident.isdigit() and ident.isascii():
        return (0, int(ident), "")
    return (1, 0, ident)


def _parse(version):
    """Return a sort key for a version string; raise ValueError if invalid."""
    if not isinstance(version, str):
        raise ValueError(f"version must be a string, got {type(version).__name__}")

    core_and_pre, plus, build = version.partition("+")
    if plus and not build:
        raise ValueError(f"empty build metadata in {version!r}")
    if plus and not all(_IDENT_RE.fullmatch(b) for b in build.split(".")):
        raise ValueError(f"invalid build metadata in {version!r}")

    core, dash, pre = core_and_pre.partition("-")
    if not _CORE_RE.fullmatch(core):
        raise ValueError(f"invalid core version in {version!r}")

    major, minor, patch = (int(p) for p in core.split("."))

    if dash:
        idents = pre.split(".")
        for ident in idents:
            if not _IDENT_RE.fullmatch(ident):
                raise ValueError(f"invalid prerelease identifier {ident!r} in {version!r}")
        # A prerelease sorts below the release (1 > 0 at this position).
        pre_key = (0, tuple(_ident_key(i) for i in idents))
    else:
        pre_key = (1,)

    return (major, minor, patch, pre_key)


def compare(a, b):
    """Return -1, 0 or 1 according to semver precedence of a versus b."""
    ka = _parse(a)
    kb = _parse(b)
    if ka < kb:
        return -1
    if ka > kb:
        return 1
    return 0


def sort_versions(versions):
    """Return a new list sorted ascending by precedence (stable)."""
    keyed = [(_parse(v), v) for v in versions]
    keyed.sort(key=lambda kv: kv[0])
    return [v for _, v in keyed]

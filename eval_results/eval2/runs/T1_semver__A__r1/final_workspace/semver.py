"""Semantic version (semver 2.0.0) precedence comparison."""

from functools import cmp_to_key

_DIGITS = frozenset("0123456789")


def _is_numeric(text):
    return len(text) > 0 and all(ch in _DIGITS for ch in text)


def _parse(version):
    """Return the precedence key for a version string.

    Raises ValueError for invalid input.
    """
    if not isinstance(version, str):
        raise ValueError(f"version must be a string, got {type(version).__name__}")

    # Build metadata is ignored entirely.
    main = version.split("+", 1)[0]

    # Prerelease starts at the first hyphen; everything before is the core.
    if "-" in main:
        core, prerelease = main.split("-", 1)
    else:
        core, prerelease = main, None

    parts = core.split(".")
    if len(parts) != 3 or not all(_is_numeric(p) for p in parts):
        raise ValueError(f"invalid version core: {version!r}")
    major, minor, patch = (int(p) for p in parts)

    if prerelease is None:
        # A release has higher precedence than any prerelease of the same core.
        return (major, minor, patch, 1, ())

    identifiers = prerelease.split(".")
    if any(ident == "" for ident in identifiers):
        raise ValueError(f"empty prerelease identifier: {version!r}")

    pre_key = tuple(
        (0, int(ident), "") if _is_numeric(ident) else (1, 0, ident)
        for ident in identifiers
    )
    return (major, minor, patch, 0, pre_key)


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
    return sorted(versions, key=cmp_to_key(compare))

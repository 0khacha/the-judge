"""Semantic version comparison following semver 2.0.0 precedence rules."""

import re

_DIGITS = re.compile(r"[0-9]+\Z")
_IDENT = re.compile(r"[0-9A-Za-z-]+\Z")


def _identifier_key(identifier):
    # Numeric identifiers sort before alphanumeric ones; numeric ones compare
    # by integer value, alphanumeric ones lexically (ASCII).
    if _DIGITS.match(identifier):
        return (0, int(identifier), "")
    return (1, 0, identifier)


def _key(version):
    """Return a sort key implementing semver precedence. Raises ValueError."""
    if not isinstance(version, str):
        raise ValueError(f"version must be a string, got {type(version).__name__}")

    rest, _, build = version.partition("+")
    if "+" in build:
        raise ValueError(f"invalid build metadata in {version!r}")
    if "+" in version and not build:
        raise ValueError(f"empty build metadata in {version!r}")
    if "+" in version:
        for ident in build.split("."):
            if not _IDENT.match(ident):
                raise ValueError(f"invalid build identifier in {version!r}")

    core, dash, prerelease = rest.partition("-")
    parts = core.split(".")
    if len(parts) != 3 or not all(_DIGITS.match(p) for p in parts):
        raise ValueError(f"invalid version core in {version!r}")
    major, minor, patch = (int(p) for p in parts)

    if not dash:
        # A release has higher precedence than any prerelease of the same core.
        return (major, minor, patch, 1, ())

    idents = prerelease.split(".")
    for ident in idents:
        if not ident:
            raise ValueError(f"empty prerelease identifier in {version!r}")
        if not _IDENT.match(ident):
            raise ValueError(f"invalid prerelease identifier in {version!r}")
    return (major, minor, patch, 0, tuple(_identifier_key(i) for i in idents))


def compare(a, b):
    """Return -1, 0 or 1 as version ``a`` is lower than, equal to, or higher than ``b``."""
    ka = _key(a)
    kb = _key(b)
    if ka < kb:
        return -1
    if ka > kb:
        return 1
    return 0


def sort_versions(versions):
    """Return a new list of versions sorted ascending by semver precedence.

    The sort is stable: versions with equal precedence keep their input order.
    """
    keyed = [(_key(v), v) for v in versions]
    keyed.sort(key=lambda pair: pair[0])
    return [v for _, v in keyed]

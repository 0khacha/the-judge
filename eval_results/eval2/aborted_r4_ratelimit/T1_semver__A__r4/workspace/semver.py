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
    prerelease = pre_split[1] if len(pre_split) > 1 else None

    match = _CORE_RE.match(core)
    if not match:
        raise ValueError(f"invalid version core: {version!r}")
    core_parts = tuple(int(part) for part in match.groups())

    pre_ids = None
    if prerelease is not None:
        pre_ids = prerelease.split(".")
        for ident in pre_ids:
            if ident == "":
                raise ValueError(f"empty prerelease identifier: {version!r}")
            if not re.match(r"^[0-9A-Za-z-]+$", ident):
                raise ValueError(f"invalid prerelease identifier: {version!r}")

    return core_parts, pre_ids


def _ident_key(ident):
    # Numeric identifiers sort before non-numeric ones; numeric compared as ints.
    if _NUMERIC_RE.match(ident):
        return (0, int(ident), "")
    return (1, 0, ident)


def _compare_prerelease(a_ids, b_ids):
    for a_id, b_id in zip(a_ids, b_ids):
        ka, kb = _ident_key(a_id), _ident_key(b_id)
        if ka != kb:
            return -1 if ka < kb else 1
    if len(a_ids) == len(b_ids):
        return 0
    return -1 if len(a_ids) < len(b_ids) else 1


def compare(a, b):
    """Return -1, 0 or 1 comparing semver strings a and b (build metadata ignored)."""
    a_core, a_pre = _parse(a)
    b_core, b_pre = _parse(b)

    if a_core != b_core:
        return -1 if a_core < b_core else 1

    if a_pre is None and b_pre is None:
        return 0
    if a_pre is None:
        return 1
    if b_pre is None:
        return -1
    return _compare_prerelease(a_pre, b_pre)


def sort_versions(versions):
    """Return a new list sorted ascending by precedence (stable for equal precedence)."""
    import functools

    return sorted(versions, key=functools.cmp_to_key(compare))

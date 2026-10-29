"""Semantic version (semver 2.0.0) precedence comparison and sorting."""

_DIGITS = frozenset("0123456789")


def _is_numeric(text):
    return len(text) > 0 and all(ch in _DIGITS for ch in text)


def _precedence_key(version):
    """Return a sortable key implementing semver 2.0.0 precedence."""
    if not isinstance(version, str):
        raise ValueError(f"version must be a string, got {type(version).__name__}")

    # Build metadata (after the first '+') is ignored for precedence.
    core_and_pre = version.split("+", 1)[0]

    # Prerelease starts at the first '-'.
    if "-" in core_and_pre:
        core_text, pre_text = core_and_pre.split("-", 1)
    else:
        core_text, pre_text = core_and_pre, None

    core_parts = core_text.split(".")
    if len(core_parts) != 3 or not all(_is_numeric(p) for p in core_parts):
        raise ValueError(f"invalid version core: {version!r}")
    core = tuple(int(p) for p in core_parts)

    if pre_text is None:
        # A release has higher precedence than any prerelease of the same core.
        return (core, 1, ())

    pre_keys = []
    for ident in pre_text.split("."):
        if ident == "":
            raise ValueError(f"empty prerelease identifier: {version!r}")
        if _is_numeric(ident):
            # Numeric identifiers sort before alphanumeric ones.
            pre_keys.append((0, int(ident), ""))
        else:
            pre_keys.append((1, 0, ident))
    return (core, 0, tuple(pre_keys))


def compare(a, b):
    """Return -1, 0 or 1 if version ``a`` is lower, equal or higher than ``b``."""
    ka = _precedence_key(a)
    kb = _precedence_key(b)
    if ka < kb:
        return -1
    if ka > kb:
        return 1
    return 0


def sort_versions(versions):
    """Return a new list of versions sorted ascending by precedence (stable)."""
    return sorted(versions, key=_precedence_key)

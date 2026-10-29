"""Semantic versions (SemVer 2.0.0) and version range matching."""

import operator

_DIGITS = frozenset("0123456789")
_IDENT_CHARS = frozenset(
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-"
)
_WILDCARDS = ("*", "x", "X")


def _is_numeric_text(text):
    return bool(text) and all(c in _DIGITS for c in text)


def _check_ident(ident, text, strict):
    """Validate one prerelease/build identifier."""
    if not isinstance(ident, str) or not ident:
        raise ValueError(f"invalid version {text!r}: empty identifier")
    if not all(c in _IDENT_CHARS for c in ident):
        raise ValueError(f"invalid version {text!r}: bad identifier {ident!r}")
    if strict and _is_numeric_text(ident) and len(ident) > 1 and ident[0] == "0":
        raise ValueError(f"invalid version {text!r}: leading zero in {ident!r}")


def _identifiers(part, text, strict):
    idents = part.split(".")
    for ident in idents:
        _check_ident(ident, text, strict)
    return tuple(idents)


def _check_num(piece, text):
    if not _is_numeric_text(piece) or (len(piece) > 1 and piece[0] == "0"):
        raise ValueError(f"invalid version {text!r}: bad number {piece!r}")
    return int(piece)


def _split_version(text, *, partial):
    """Split version text into (parts, prerelease, build).

    ``parts`` is a list of three entries: ints, or None for a wildcard
    position. Partial versions (only when ``partial`` is true) are padded
    with None. Raises ValueError for malformed text, TypeError for non-str.
    """
    if not isinstance(text, str):
        raise TypeError(f"version must be a str, not {type(text).__name__}")
    body = text
    had_v = body.startswith("v")
    if had_v:
        body = body[1:]
    build = ()
    if "+" in body:
        body, build_text = body.split("+", 1)
        build = _identifiers(build_text, text, strict=False)
    prerelease = ()
    if "-" in body:
        body, pre_text = body.split("-", 1)
        prerelease = _identifiers(pre_text, text, strict=True)

    pieces = body.split(".")
    if len(pieces) > 3:
        raise ValueError(f"invalid version {text!r}: too many parts")
    if had_v and pieces[0] in _WILDCARDS:
        raise ValueError(f"invalid version {text!r}: wildcard after 'v'")
    parts = []
    seen_wildcard = False
    for piece in pieces:
        if piece in _WILDCARDS:
            if not partial:
                raise ValueError(f"invalid version {text!r}: wildcard not allowed")
            seen_wildcard = True
            parts.append(None)
        else:
            if seen_wildcard:
                raise ValueError(f"invalid version {text!r}: number after wildcard")
            parts.append(_check_num(piece, text))
    if len(parts) < 3:
        if not partial:
            raise ValueError(f"invalid version {text!r}: expected MAJOR.MINOR.PATCH")
        if prerelease or build:
            raise ValueError(f"invalid version {text!r}: partial version with suffix")
        parts += [None] * (3 - len(parts))
    if None in parts and (prerelease or build):
        raise ValueError(f"invalid version {text!r}: wildcard with suffix")
    return parts, prerelease, build


def _ident_key(ident):
    if _is_numeric_text(ident):
        return (0, int(ident), "")
    return (1, 0, ident)


def _pre_key(prerelease):
    # A release (no prerelease) sorts above every prerelease of the same core.
    if not prerelease:
        return (1,)
    return (0, tuple(_ident_key(i) for i in prerelease))


class Version:
    """A semantic version. Build metadata is ignored for comparison."""

    __slots__ = ("major", "minor", "patch", "prerelease", "build")

    def __init__(self, major, minor, patch, prerelease=(), build=()):
        for name, value in (("major", major), ("minor", minor), ("patch", patch)):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an int")
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
        pre = tuple(prerelease)
        bld = tuple(build)
        for ident in pre:
            _check_ident(ident, ident, strict=True)
        for ident in bld:
            _check_ident(ident, ident, strict=False)
        self.major = major
        self.minor = minor
        self.patch = patch
        self.prerelease = pre
        self.build = bld

    @property
    def _key(self):
        return (self.major, self.minor, self.patch, _pre_key(self.prerelease))

    def __str__(self):
        text = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            text += "-" + ".".join(self.prerelease)
        if self.build:
            text += "+" + ".".join(self.build)
        return text

    def __repr__(self):
        return f"Version({str(self)!r})"

    def __eq__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self._key == other._key

    def __ne__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self._key != other._key

    def __lt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self._key < other._key

    def __le__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self._key <= other._key

    def __gt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self._key > other._key

    def __ge__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self._key >= other._key

    def __hash__(self):
        return hash(self._key)


def parse(text):
    """Parse a strict SemVer string (optional leading 'v') into a Version."""
    parts, prerelease, build = _split_version(text, partial=False)
    return Version(parts[0], parts[1], parts[2], prerelease, build)


def _as_version(value):
    if isinstance(value, Version):
        return value
    return parse(value)


def compare(a, b):
    """Return -1, 0 or 1 comparing two version strings by precedence."""
    ka = _as_version(a)._key
    kb = _as_version(b)._key
    return (ka > kb) - (ka < kb)


# ---------------------------------------------------------------- ranges

_OP_TESTS = {
    "==": operator.eq,
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
}


def _base_if_pre(version):
    """(M, m, p) when the written version carries a prerelease, else None."""
    if version.prerelease:
        return (version.major, version.minor, version.patch)
    return None


def _release_key(major, minor, patch):
    return (major, minor, patch, _pre_key(()))


def _caret(text):
    version = parse(text)
    if version.major > 0:
        upper = Version(version.major + 1, 0, 0)
    elif version.minor > 0:
        upper = Version(0, version.minor + 1, 0)
    else:
        upper = Version(0, 0, version.patch + 1)
    return [(">=", version._key), ("<", upper._key)], _base_if_pre(version)


def _tilde(text):
    if any(piece in _WILDCARDS for piece in text.split(".")):
        raise ValueError(f"invalid tilde operand {text!r}: wildcards not allowed")
    parts, prerelease, build = _split_version(text, partial=True)
    major, minor, patch = parts
    if minor is None:
        lower = Version(major, 0, 0)
        upper = Version(major + 1, 0, 0)
        base = None
    else:
        lower = Version(major, minor, 0 if patch is None else patch, prerelease)
        upper = Version(major, minor + 1, 0)
        base = (major, minor, patch) if prerelease else None
    return [(">=", lower._key), ("<", upper._key)], base


def _compile_token(token):
    """Return (constraints, prerelease_base) for one comparator token.

    constraints is a list of (operator name, key) pairs that must all hold.
    prerelease_base is (M, m, p) if the comparator was written with a
    prerelease on that core version, else None.
    """
    if token in _WILDCARDS:
        return [], None
    for op in (">=", "<=", ">", "<"):
        if token.startswith(op):
            version = parse(token[len(op):])
            return [(op, version._key)], _base_if_pre(version)
    if token.startswith("="):
        version = parse(token[1:])
        return [("==", version._key)], _base_if_pre(version)
    if token.startswith("^"):
        return _caret(token[1:])
    if token.startswith("~"):
        return _tilde(token[1:])

    parts, prerelease, build = _split_version(token, partial=True)
    if None not in parts:
        version = Version(parts[0], parts[1], parts[2], prerelease, build)
        return [("==", version._key)], _base_if_pre(version)

    major, minor, _patch = parts
    if minor is None:
        lower = _release_key(major, 0, 0)
        upper = _release_key(major + 1, 0, 0)
    else:
        lower = _release_key(major, minor, 0)
        upper = _release_key(major, minor + 1, 0)
    return [(">=", lower), ("<", upper)], None


def _compile_range(range_text):
    """Compile a range into a list of (constraints, prerelease_bases) sets."""
    if not isinstance(range_text, str):
        raise TypeError(f"range must be a str, not {type(range_text).__name__}")
    compiled = []
    for set_text in range_text.split("||"):
        constraints = []
        bases = set()
        for token in set_text.split():
            token_constraints, base = _compile_token(token)
            constraints.extend(token_constraints)
            if base is not None:
                bases.add(base)
        compiled.append((constraints, frozenset(bases)))
    return compiled


def _matches(compiled, version):
    key = version._key
    has_prerelease = bool(version.prerelease)
    core = (version.major, version.minor, version.patch)
    for constraints, bases in compiled:
        if has_prerelease and core not in bases:
            continue
        if all(_OP_TESTS[op](key, bound) for op, bound in constraints):
            return True
    return False


def satisfies(version, range_text):
    """True if ``version`` (str or Version) satisfies the range text."""
    value = _as_version(version)
    return _matches(_compile_range(range_text), value)


def max_satisfying(versions, range_text):
    """Highest entry of ``versions`` satisfying the range, as given, or None."""
    compiled = _compile_range(range_text)
    best = None
    best_version = None
    for item in versions:
        value = _as_version(item)
        if not _matches(compiled, value):
            continue
        if best_version is None or value._key > best_version._key:
            best = item
            best_version = value
    return best


def sort_versions(versions, reverse=False):
    """New list of the input entries sorted by precedence (stable)."""
    pairs = [(item, _as_version(item)) for item in versions]
    pairs.sort(key=lambda pair: pair[1]._key, reverse=reverse)
    return [item for item, _ in pairs]

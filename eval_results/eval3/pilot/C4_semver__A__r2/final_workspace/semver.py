"""Semantic versions (SemVer 2.0.0) and range matching. Standard library only."""

import operator
import re

__all__ = [
    "Version",
    "parse",
    "compare",
    "satisfies",
    "max_satisfying",
    "sort_versions",
]

_NUM = r"(?:0|[1-9][0-9]*)"
_IDENT = r"[0-9A-Za-z-]+"
_DOTTED = _IDENT + r"(?:\." + _IDENT + r")*"
_FULL_RE = re.compile(
    r"(?P<major>" + _NUM + r")\.(?P<minor>" + _NUM + r")\.(?P<patch>" + _NUM + r")"
    r"(?:-(?P<pre>" + _DOTTED + r"))?"
    r"(?:\+(?P<build>" + _DOTTED + r"))?"
)
_NUM_RE = re.compile(_NUM)
_IDENT_RE = re.compile(_IDENT)
_DIGITS_RE = re.compile(r"[0-9]+")

_WILDCARDS = ("*", "x", "X")
# Longer operators must come first so that ">=" is not read as ">".
_OPS = (">=", "<=", ">", "<", "=", "^", "~")
_SIMPLE_OPS = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
}


def _identifiers(value, name, check_numeric):
    if isinstance(value, str):
        raise TypeError(f"{name} must be a sequence of strings, not str")
    try:
        items = tuple(value)
    except TypeError:
        raise TypeError(f"{name} must be a sequence of strings") from None
    for item in items:
        if not isinstance(item, str):
            raise TypeError(f"{name} identifiers must be str")
        if not _IDENT_RE.fullmatch(item):
            raise ValueError(f"invalid {name} identifier: {item!r}")
        if check_numeric and _DIGITS_RE.fullmatch(item) and len(item) > 1 and item[0] == "0":
            raise ValueError(f"numeric {name} identifier has leading zero: {item!r}")
    return items


class Version:
    """A semantic version. Build metadata is ignored for comparison and hashing."""

    __slots__ = ("major", "minor", "patch", "prerelease", "build")

    def __init__(self, major, minor, patch, prerelease=(), build=()):
        for name, value in (("major", major), ("minor", minor), ("patch", patch)):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an int")
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
        self.major = major
        self.minor = minor
        self.patch = patch
        self.prerelease = _identifiers(prerelease, "prerelease", True)
        self.build = _identifiers(build, "build", False)

    def _precedence(self):
        if not self.prerelease:
            pre_key = (1,)
        else:
            pre_key = (
                0,
                tuple(
                    (0, int(i)) if _DIGITS_RE.fullmatch(i) else (1, i)
                    for i in self.prerelease
                ),
            )
        return (self.major, self.minor, self.patch, pre_key)

    def __eq__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self._precedence() == other._precedence()

    def __ne__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self._precedence() != other._precedence()

    def __lt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self._precedence() < other._precedence()

    def __le__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self._precedence() <= other._precedence()

    def __gt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self._precedence() > other._precedence()

    def __ge__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self._precedence() >= other._precedence()

    def __hash__(self):
        return hash(self._precedence())

    def __str__(self):
        text = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            text += "-" + ".".join(self.prerelease)
        if self.build:
            text += "+" + ".".join(self.build)
        return text

    def __repr__(self):
        return (
            f"Version({self.major}, {self.minor}, {self.patch}, "
            f"{self.prerelease!r}, {self.build!r})"
        )


def _version_from_match(match):
    pre = match.group("pre")
    build = match.group("build")
    return Version(
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
        tuple(pre.split(".")) if pre else (),
        tuple(build.split(".")) if build else (),
    )


def parse(text):
    """Parse ``MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]`` with an optional leading ``v``."""
    if not isinstance(text, str):
        raise TypeError("version must be a str")
    body = text[1:] if text.startswith("v") else text
    match = _FULL_RE.fullmatch(body)
    if not match:
        raise ValueError(f"invalid version: {text!r}")
    return _version_from_match(match)


def _coerce(value):
    if isinstance(value, Version):
        return value
    if isinstance(value, str):
        return parse(value)
    raise TypeError("version must be a str or Version")


def compare(a, b):
    """Return -1, 0 or 1 comparing two version strings by precedence."""
    va = _coerce(a)
    vb = _coerce(b)
    if va < vb:
        return -1
    if va > vb:
        return 1
    return 0


# A comparator is (constraints, pre) where constraints is a list of
# (operator function, Version) pairs and pre is the (major, minor, patch)
# triple of a prerelease written in the comparator, or None.


def _partial_bounds(body, allow_wildcard):
    parts = body.split(".")
    if len(parts) > 3 or parts[0] in _WILDCARDS:
        raise ValueError(f"invalid partial version: {body!r}")
    nums = []
    wild = False
    for part in parts:
        if part in _WILDCARDS:
            if not allow_wildcard:
                raise ValueError(f"wildcard not allowed here: {body!r}")
            wild = True
        elif wild or not _NUM_RE.fullmatch(part):
            raise ValueError(f"invalid partial version: {body!r}")
        else:
            nums.append(int(part))
    if len(nums) == 1:
        lo = Version(nums[0], 0, 0)
        hi = Version(nums[0] + 1, 0, 0)
    elif len(nums) == 2:
        lo = Version(nums[0], nums[1], 0)
        hi = Version(nums[0], nums[1] + 1, 0)
    else:
        raise ValueError(f"invalid partial version: {body!r}")
    return [(operator.ge, lo), (operator.lt, hi)]


def _caret_upper(v):
    if v.major > 0:
        return Version(v.major + 1, 0, 0)
    if v.minor > 0:
        return Version(0, v.minor + 1, 0)
    return Version(0, 0, v.patch + 1)


def _parse_comparator(token):
    op = next((o for o in _OPS if token.startswith(o)), "")
    body = token[len(op):]
    if body in _WILDCARDS:
        if op:
            raise ValueError(f"invalid comparator: {token!r}")
        return ([], None)
    if body.startswith("v"):
        body = body[1:]

    full = _FULL_RE.fullmatch(body)
    if full:
        v = _version_from_match(full)
        pre = (v.major, v.minor, v.patch) if v.prerelease else None
        if op in ("", "="):
            cons = [(operator.eq, v)]
        elif op in _SIMPLE_OPS:
            cons = [(_SIMPLE_OPS[op], v)]
        elif op == "^":
            cons = [(operator.ge, v), (operator.lt, _caret_upper(v))]
        else:  # "~"
            cons = [(operator.ge, v), (operator.lt, Version(v.major, v.minor + 1, 0))]
        return (cons, pre)

    if op == "":
        return (_partial_bounds(body, allow_wildcard=True), None)
    if op == "~":
        return (_partial_bounds(body, allow_wildcard=False), None)
    raise ValueError(f"invalid comparator: {token!r}")


def _parse_range(range_text):
    if not isinstance(range_text, str):
        raise TypeError("range must be a str")
    sets = []
    for raw in range_text.split("||"):
        sets.append([_parse_comparator(tok) for tok in raw.split()])
    return sets


def _set_matches(comparators, v):
    if v.prerelease:
        triple = (v.major, v.minor, v.patch)
        if not any(pre == triple for _, pre in comparators):
            return False
    return all(
        op(v, bound)
        for cons, _ in comparators
        for op, bound in cons
    )


def satisfies(version, range_text):
    """Return True if ``version`` satisfies the range expression ``range_text``."""
    v = _coerce(version)
    sets = _parse_range(range_text)
    return any(_set_matches(s, v) for s in sets)


def max_satisfying(versions, range_text):
    """Return the highest entry (as given) satisfying the range, or None."""
    sets = _parse_range(range_text)
    best = None
    best_version = None
    for item in versions:
        v = _coerce(item)
        if any(_set_matches(s, v) for s in sets):
            if best_version is None or v > best_version:
                best = item
                best_version = v
    return best


def sort_versions(versions, reverse=False):
    """Return a new list of the entries sorted by precedence (stable)."""
    pairs = [(item, _coerce(item)) for item in versions]
    pairs.sort(key=lambda pair: pair[1], reverse=reverse)
    return [item for item, _ in pairs]

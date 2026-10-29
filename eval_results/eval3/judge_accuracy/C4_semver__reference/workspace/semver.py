import re

_NUM = r"(0|[1-9][0-9]*)"
_ALNUM = r"[0-9A-Za-z-]+"
_PRE_ID = r"(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)"
_VERSION_RE = re.compile(
    r"v?%s\.%s\.%s(?:-(%s(?:\.%s)*))?(?:\+(%s(?:\.%s)*))?" % (_NUM, _NUM, _NUM, _PRE_ID, _PRE_ID, _ALNUM, _ALNUM)
)
_PARTIAL_RE = re.compile(r"v?([0-9]+|[xX*])(?:\.([0-9]+|[xX*]))?(?:\.([0-9]+|[xX*]))?")


class Version:
    __slots__ = ("major", "minor", "patch", "prerelease", "build")

    def __init__(self, major, minor, patch, prerelease=(), build=()):
        self.major = major
        self.minor = minor
        self.patch = patch
        self.prerelease = tuple(prerelease)
        self.build = tuple(build)

    def _key(self):
        if not self.prerelease:
            pre = (1,)
        else:
            ids = []
            for ident in self.prerelease:
                if ident.isdigit():
                    ids.append((0, int(ident), ""))
                else:
                    ids.append((1, 0, ident))
            pre = (0, tuple(ids))
        return (self.major, self.minor, self.patch, pre)

    def __eq__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self._key() == other._key()

    def __lt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self._key() < other._key()

    def __le__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self._key() <= other._key()

    def __gt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self._key() > other._key()

    def __ge__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self._key() >= other._key()

    def __hash__(self):
        return hash(self._key())

    def __str__(self):
        s = "%d.%d.%d" % (self.major, self.minor, self.patch)
        if self.prerelease:
            s += "-" + ".".join(self.prerelease)
        if self.build:
            s += "+" + ".".join(self.build)
        return s

    def __repr__(self):
        return "Version(%r)" % str(self)


def parse(text):
    if not isinstance(text, str):
        raise TypeError("version must be a str")
    m = _VERSION_RE.fullmatch(text)
    if not m:
        raise ValueError("invalid version: %r" % text)
    pre = tuple(m.group(4).split(".")) if m.group(4) else ()
    build = tuple(m.group(5).split(".")) if m.group(5) else ()
    return Version(int(m.group(1)), int(m.group(2)), int(m.group(3)), pre, build)


def _as_version(v):
    return v if isinstance(v, Version) else parse(v)


def compare(a, b):
    va, vb = _as_version(a), _as_version(b)
    if va < vb:
        return -1
    if va > vb:
        return 1
    return 0


def _comparators(token):
    """Return a list of (op, Version) for one token."""
    if token in ("*", "x", "X"):
        return []
    for op in (">=", "<=", ">", "<", "="):
        if token.startswith(op):
            return [(op, parse(token[len(op):]))]
    if token[0] == "^":
        v = parse(token[1:])
        if v.major > 0:
            upper = Version(v.major + 1, 0, 0)
        elif v.minor > 0:
            upper = Version(0, v.minor + 1, 0)
        else:
            upper = Version(0, 0, v.patch + 1)
        return [(">=", v), ("<", upper)]
    if token[0] == "~":
        rest = token[1:]
        m = _PARTIAL_RE.fullmatch(rest)
        if m and m.group(2) is not None and m.group(3) is None and not (
                m.group(1) in "xX*" or m.group(2) in "xX*"):
            major, minor = int(m.group(1)), int(m.group(2))
            return [(">=", Version(major, minor, 0)), ("<", Version(major, minor + 1, 0))]
        if m and m.group(2) is None and m.group(1) not in ("x", "X", "*"):
            major = int(m.group(1))
            return [(">=", Version(major, 0, 0)), ("<", Version(major + 1, 0, 0))]
        v = parse(rest)
        return [(">=", v), ("<", Version(v.major, v.minor + 1, 0))]
    try:
        return [("=", parse(token))]
    except ValueError:
        pass
    m = _PARTIAL_RE.fullmatch(token)
    if not m:
        raise ValueError("invalid range comparator: %r" % token)
    parts = [m.group(1), m.group(2), m.group(3)]
    wild = ("x", "X", "*")
    seen_wild = False
    nums = []
    for p in parts:
        if p is None or p in wild:
            seen_wild = True
            continue
        if seen_wild:
            raise ValueError("invalid range comparator: %r" % token)
        if len(p) > 1 and p[0] == "0":
            raise ValueError("invalid range comparator: %r" % token)
        nums.append(int(p))
    if not nums:
        return []
    if len(nums) == 1:
        return [(">=", Version(nums[0], 0, 0)), ("<", Version(nums[0] + 1, 0, 0))]
    if len(nums) == 2:
        return [(">=", Version(nums[0], nums[1], 0)), ("<", Version(nums[0], nums[1] + 1, 0))]
    raise ValueError("invalid range comparator: %r" % token)


_OPS = {
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    "=": lambda a, b: a == b,
}


def _parse_range(range_text):
    if not isinstance(range_text, str):
        raise TypeError("range must be a str")
    sets = []
    for part in range_text.split("||"):
        comps = []
        for token in part.split():
            comps.extend(_comparators(token))
        sets.append(comps)
    return sets


def satisfies(version, range_text):
    v = _as_version(version)
    sets = _parse_range(range_text)
    for comps in sets:
        if not all(_OPS[op](v, c) for op, c in comps):
            continue
        if v.prerelease:
            if not any(c.prerelease and (c.major, c.minor, c.patch) == (v.major, v.minor, v.patch)
                       for _, c in comps):
                continue
        return True
    return False


def max_satisfying(versions, range_text):
    best = None
    best_v = None
    sets_checked = _parse_range(range_text)  # validate range even for empty list
    del sets_checked
    for s in versions:
        v = parse(s)
        if satisfies(v, range_text):
            if best_v is None or v > best_v:
                best, best_v = s, v
    return best


def sort_versions(versions, reverse=False):
    parsed = [(parse(s), s) for s in versions]
    parsed.sort(key=lambda p: p[0]._key(), reverse=reverse)
    return [s for _, s in parsed]

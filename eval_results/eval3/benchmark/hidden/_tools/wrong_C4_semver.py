PATCHES = {
    1: {"semver.py": [
        ('ids.append((0, int(ident), ""))', 'ids.append((0, 0, ident))'),
        ("        if v.major > 0:\n            upper = Version(v.major + 1, 0, 0)\n        elif v.minor > 0:", "        if True:\n            upper = Version(v.major + 1, 0, 0)\n        elif v.minor > 0:"),
    ]},
    2: {"semver.py": [
        ("        if v.prerelease:\n            if not any(", "        if False:\n            if not any("),
        ("_VERSION_RE.fullmatch(text)", "_VERSION_RE.match(text)"),
    ]},
}

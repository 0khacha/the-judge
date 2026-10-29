PATCHES = {
    1: {"wrap.py": [
        ("def _cw(ch):\n", "def _cw(ch):\n    return 1\n"),
    ]},
    2: {"wrap.py": [
        ('re.split(r"[ \\t\\n]+", " ".join(p))', '" ".join(p).split()'),
        (' and word[i - 1].isalnum() and word[i + 1].isalnum()', ' and False'),
    ]},
}

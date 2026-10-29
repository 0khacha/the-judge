PATCHES = {
    1: {"tmpl/engine.py": [
        (""".replace('"', "&quot;").replace("'", "&#x27;"))""", """.replace('"', "&quot;"))"""),
        ("                child = dict(ctx)\n", "                child = ctx\n"),
    ]},
    2: {"tmpl/lexer.py": [
        ('        line += src.count("\\n", m.start(), end + 2)\n', "        pass\n"),
        ("tokens[i - 1][1].rstrip()", 'tokens[i - 1][1].rstrip(" \\t")'),
    ]},
}

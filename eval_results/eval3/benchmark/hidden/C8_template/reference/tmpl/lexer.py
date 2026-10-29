import re

from .errors import TemplateError

_OPEN = re.compile(r"\{\{|\{%|\{#")
_CLOSE = {"{{": "}}", "{%": "%}", "{#": "#}"}
_KIND = {"{{": "var", "{%": "tag", "{#": "comment"}
_ENDRAW = re.compile(r"\{%-?\s*endraw\s*-?%\}")


def tokenize(src):
    """Return a list of [kind, value, line, lstrip, rstrip] tokens (kind: text/var/tag/comment)."""
    tokens = []
    pos = 0
    line = 1
    n = len(src)
    while pos < n:
        m = _OPEN.search(src, pos)
        if not m:
            tokens.append(["text", src[pos:], line, False, False])
            break
        if m.start() > pos:
            tokens.append(["text", src[pos:m.start()], line, False, False])
            line += src.count("\n", pos, m.start())
        opener = m.group()
        close = _CLOSE[opener]
        end = src.find(close, m.end())
        if end < 0:
            raise TemplateError("unclosed %s" % opener, line)
        inner = src[m.end():end]
        lstrip = inner.startswith("-")
        rstrip = inner.endswith("-") and len(inner) > (1 if lstrip else 0)
        if lstrip:
            inner = inner[1:]
        if rstrip:
            inner = inner[:-1]
        tokens.append([_KIND[opener], inner.strip(), line, lstrip, rstrip])
        tag_line = line
        line += src.count("\n", m.start(), end + 2)
        pos = end + 2
        if opener == "{%" and inner.strip() == "raw":
            em = _ENDRAW.search(src, pos)
            if not em:
                raise TemplateError("unclosed raw block", tag_line)
            if em.start() > pos:
                tokens.append(["text", src[pos:em.start()], line, False, False])
                line += src.count("\n", pos, em.start())
            # let the main loop tokenize the endraw tag
            pos = em.start()
            tokens.append(["rawmark", "", line, False, False])
    # apply whitespace control
    out = []
    for i, tok in enumerate(tokens):
        if tok[0] == "rawmark":
            continue
        out.append(tok)
    tokens = out
    for i, tok in enumerate(tokens):
        if tok[0] in ("var", "tag", "comment"):
            if tok[3] and i > 0 and tokens[i - 1][0] == "text":
                tokens[i - 1][1] = tokens[i - 1][1].rstrip()
            if tok[4] and i + 1 < len(tokens) and tokens[i + 1][0] == "text":
                tokens[i + 1][1] = tokens[i + 1][1].lstrip()
    return tokens

import re

from .errors import TemplateError
from .lexer import tokenize

_MISSING = object()
_FIRST = r"[A-Za-z_][A-Za-z0-9_]*"
_PATH_RE = re.compile(r"%s(?:\.[A-Za-z0-9_]+)*" % _FIRST)
_FILTER_RE = re.compile(r'\s*\|\s*([A-Za-z_][A-Za-z0-9_]*)(?::"((?:[^"\\]|\\.)*)")?')
_FOR_RE = re.compile(r"(%s)\s+in\s+(%s)" % (_FIRST, r"%s(?:\.[A-Za-z0-9_]+)*" % _FIRST))
_FILTERS = {"upper": False, "lower": False, "length": False, "safe": False, "default": True, "join": True}


def _parse_path(text, line):
    if not _PATH_RE.fullmatch(text):
        raise TemplateError("invalid variable path %r" % text, line)
    return text


def _parse_var(text, line):
    m = re.match(r"[A-Za-z0-9_.]*", text)
    path = _parse_path(m.group(), line)
    rest = text[m.end():]
    filters = []
    pos = 0
    while pos < len(rest):
        fm = _FILTER_RE.match(rest, pos)
        if not fm:
            if rest[pos:].strip() == "":
                break
            raise TemplateError("malformed expression %r" % text, line)
        name, arg = fm.group(1), fm.group(2)
        if name not in _FILTERS:
            raise TemplateError("unknown filter %r" % name, line)
        if _FILTERS[name] and arg is None:
            raise TemplateError("filter %r requires an argument" % name, line)
        if not _FILTERS[name] and arg is not None:
            raise TemplateError("filter %r takes no argument" % name, line)
        if arg is not None:
            arg = re.sub(r"\\(.)", r"\1", arg)
        filters.append((name, arg))
        pos = fm.end()
    return path, filters


def _parse_cond(rest, line):
    words = rest.split()
    if len(words) == 1:
        return False, _parse_path(words[0], line)
    if len(words) == 2 and words[0] == "not":
        return True, _parse_path(words[1], line)
    raise TemplateError("invalid condition %r" % rest, line)


class _Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def block(self, stops):
        """Parse until a tag in `stops`; returns (nodes, stop_token_or_None). Does not consume the stop."""
        nodes = []
        toks = self.tokens
        while self.pos < len(toks):
            kind, value, line = toks[self.pos][0], toks[self.pos][1], toks[self.pos][2]
            if kind == "text":
                nodes.append(("text", value))
                self.pos += 1
            elif kind == "comment":
                self.pos += 1
            elif kind == "var":
                if value == "":
                    raise TemplateError("empty expression", line)
                path, filters = _parse_var(value, line)
                nodes.append(("var", path, filters))
                self.pos += 1
            else:
                words = value.split(None, 1)
                if not words:
                    raise TemplateError("empty tag", line)
                name = words[0]
                rest = words[1] if len(words) > 1 else ""
                if name in stops:
                    return nodes, toks[self.pos]
                self.pos += 1
                if name == "if":
                    nodes.append(self.parse_if(rest, line))
                elif name == "for":
                    nodes.append(self.parse_for(rest, line))
                elif name == "raw":
                    if rest:
                        raise TemplateError("unexpected text after raw", line)
                    nodes.append(self.parse_raw(line))
                elif name in ("endif", "endfor", "else", "elif", "endraw"):
                    raise TemplateError("unexpected %s" % name, line)
                else:
                    raise TemplateError("unknown tag %r" % name, line)
        return nodes, None

    def end_tag(self, tok, name):
        if tok[1].split(None, 1)[1:] :
            raise TemplateError("unexpected text after %s" % name, tok[2])
        self.pos += 1

    def parse_if(self, rest, line):
        branches = []
        neg, path = _parse_cond(rest, line)
        else_body = None
        body, stop = self.block({"elif", "else", "endif"})
        branches.append((neg, path, body))
        while True:
            if stop is None:
                raise TemplateError("unclosed if", line)
            name = stop[1].split(None, 1)[0]
            if name == "elif":
                neg, path = _parse_cond(stop[1].split(None, 1)[1] if len(stop[1].split(None, 1)) > 1 else "", stop[2])
                self.pos += 1
                body, stop = self.block({"elif", "else", "endif"})
                branches.append((neg, path, body))
            elif name == "else":
                self.end_tag(stop, "else")
                else_body, stop = self.block({"endif"})
                if stop is None:
                    raise TemplateError("unclosed if", line)
                self.end_tag(stop, "endif")
                break
            else:
                self.end_tag(stop, "endif")
                break
        return ("if", branches, else_body)

    def parse_for(self, rest, line):
        m = _FOR_RE.fullmatch(rest.strip())
        if not m:
            raise TemplateError("invalid for tag", line)
        var, path = m.group(1), m.group(2)
        body, stop = self.block({"else", "endfor"})
        else_body = None
        if stop is None:
            raise TemplateError("unclosed for", line)
        if stop[1].split()[0] == "else":
            self.end_tag(stop, "else")
            else_body, stop = self.block({"endfor"})
            if stop is None:
                raise TemplateError("unclosed for", line)
        self.end_tag(stop, "endfor")
        return ("for", var, path, body, else_body)

    def parse_raw(self, line):
        toks = self.tokens
        text = ""
        if self.pos < len(toks) and toks[self.pos][0] == "text":
            text = toks[self.pos][1]
            self.pos += 1
        if self.pos >= len(toks) or toks[self.pos][0] != "tag" or toks[self.pos][1].split()[:1] != ["endraw"]:
            raise TemplateError("unclosed raw block", line)
        self.end_tag(toks[self.pos], "endraw")
        return ("text", text)


def _resolve(ctx, path):
    parts = path.split(".")
    cur = ctx.get(parts[0], _MISSING)
    for seg in parts[1:]:
        if cur is _MISSING:
            break
        if isinstance(cur, dict):
            cur = cur.get(seg, _MISSING)
        elif isinstance(cur, (list, tuple)) and seg.isascii() and seg.isdigit():
            idx = int(seg)
            cur = cur[idx] if idx < len(cur) else _MISSING
        else:
            cur = _MISSING
    return cur


def _tostr(v):
    if v is _MISSING or v is None:
        return ""
    return str(v)


def _escape(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def _apply(val, filters):
    safe = False
    for name, arg in filters:
        if name == "safe":
            safe = True
        elif name == "default":
            if val is _MISSING or val is None or (isinstance(val, str) and val == ""):
                val = arg
        elif name == "upper":
            val = _tostr(val).upper()
        elif name == "lower":
            val = _tostr(val).lower()
        elif name == "length":
            val = len(val) if isinstance(val, (str, list, tuple, dict)) else 0
        elif name == "join":
            if isinstance(val, (list, tuple)):
                val = arg.join(str(x) for x in val)
    text = _tostr(val)
    return text if safe else _escape(text)


def _render(nodes, ctx, out):
    for node in nodes:
        kind = node[0]
        if kind == "text":
            out.append(node[1])
        elif kind == "var":
            out.append(_apply(_resolve(ctx, node[1]), node[2]))
        elif kind == "if":
            for neg, path, body in node[1]:
                val = _resolve(ctx, path)
                truth = False if val is _MISSING else bool(val)
                if truth != neg:
                    _render(body, ctx, out)
                    break
            else:
                if node[2] is not None:
                    _render(node[2], ctx, out)
        elif kind == "for":
            _, var, path, body, else_body = node
            val = _resolve(ctx, path)
            if val is _MISSING or val is None:
                items = []
            elif isinstance(val, dict):
                items = list(val.keys())
            elif isinstance(val, (list, tuple)):
                items = list(val)
            else:
                items = []
            if not items:
                if else_body is not None:
                    _render(else_body, ctx, out)
                continue
            n = len(items)
            for i, item in enumerate(items):
                child = ctx
                child[var] = item
                child["loop"] = {"index": i + 1, "index0": i, "first": i == 0,
                                 "last": i == n - 1, "length": n}
                _render(body, child, out)


def render(template, context=None):
    if context is None:
        context = {}
    tokens = tokenize(template)
    parser = _Parser(tokens)
    nodes, stop = parser.block(set())
    out = []
    _render(nodes, dict(context), out)
    return "".join(out)

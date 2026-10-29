"""Parser and renderer for the template language."""

import re

from .errors import TemplateError
from .lexer import TEXT, VAR, TAG, tokenize

_IDENT = r"[A-Za-z_][A-Za-z0-9_]*"
_PATH = _IDENT + r"(?:\.[A-Za-z0-9_]+)*"
_PATH_RE = re.compile(_PATH)
_NAME_RE = re.compile(_IDENT)
_COND_RE = re.compile(r"(?:(not)\s+)?(" + _PATH + r")")
_FOR_RE = re.compile(r"(" + _IDENT + r")\s+in\s+(" + _PATH + r")")

_FILTERS_WITH_ARG = ("default", "join")
_FILTERS_NO_ARG = ("upper", "lower", "length", "safe")
_IF_STOPS = ("elif", "else", "endif")
_FOR_STOPS = ("else", "endfor")

UNDEFINED = object()


# ---------------------------------------------------------------- expressions

def _skip_ws(s, i):
    while i < len(s) and s[i].isspace():
        i += 1
    return i


def _parse_string(s, i, line):
    """Parse a double-quoted string starting at s[i]; returns (value, next_index)."""
    i += 1
    buf = []
    n = len(s)
    while i < n:
        c = s[i]
        if c == "\\" and i + 1 < n and s[i + 1] in '"\\':
            buf.append(s[i + 1])
            i += 2
        elif c == '"':
            return "".join(buf), i + 1
        else:
            buf.append(c)
            i += 1
    raise TemplateError("unterminated string literal", line)


def _parse_var(content, line):
    """Parse ``path|filter|filter:"arg"``; returns (path_segments, filters)."""
    s = content
    i = _skip_ws(s, 0)
    m = _PATH_RE.match(s, i)
    if m is None:
        raise TemplateError("malformed expression", line)
    path = m.group().split(".")
    i = m.end()
    filters = []
    while True:
        i = _skip_ws(s, i)
        if i == len(s):
            break
        if s[i] != "|":
            raise TemplateError("malformed expression", line)
        i = _skip_ws(s, i + 1)
        m = _NAME_RE.match(s, i)
        if m is None:
            raise TemplateError("malformed filter", line)
        name = m.group()
        i = _skip_ws(s, m.end())
        arg = None
        if i < len(s) and s[i] == ":":
            i = _skip_ws(s, i + 1)
            if i >= len(s) or s[i] != '"':
                raise TemplateError("filter argument must be a quoted string", line)
            arg, i = _parse_string(s, i, line)
        if name not in _FILTERS_WITH_ARG + _FILTERS_NO_ARG:
            raise TemplateError("unknown filter '%s'" % name, line)
        if name in _FILTERS_WITH_ARG and arg is None:
            raise TemplateError("filter '%s' requires an argument" % name, line)
        if name in _FILTERS_NO_ARG and arg is not None:
            raise TemplateError("filter '%s' takes no argument" % name, line)
        filters.append((name, arg))
    return path, filters


# -------------------------------------------------------------------- parser

class _Parser(object):
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def parse(self):
        return self.block(())

    def block(self, stops):
        """Parse nodes until a tag in ``stops`` (not consumed) or end of input."""
        nodes = []
        toks = self.tokens
        while self.pos < len(toks):
            tok = toks[self.pos]
            if tok.kind == TEXT:
                if tok.value:
                    nodes.append(("text", tok.value))
                self.pos += 1
            elif tok.kind == VAR:
                path, filters = _parse_var(tok.value, tok.line)
                nodes.append(("var", path, filters))
                self.pos += 1
            else:
                word = tok.value[0]
                if word in stops:
                    break
                if word == "if":
                    nodes.append(self.if_block())
                elif word == "for":
                    nodes.append(self.for_block())
                else:
                    raise TemplateError("'%s' in the wrong place" % word, tok.line)
        return nodes

    def closer(self, opener):
        """Return the tag at the current position, or raise if the block is unclosed."""
        if self.pos >= len(self.tokens):
            raise TemplateError("unclosed '%s' block" % opener.value[0], opener.line)
        return self.tokens[self.pos]

    @staticmethod
    def no_args(tok):
        if tok.value[1]:
            raise TemplateError("malformed '%s' tag" % tok.value[0], tok.line)

    @staticmethod
    def condition(tok):
        word, rest = tok.value
        m = _COND_RE.fullmatch(rest)
        if m is None:
            raise TemplateError("malformed '%s' condition" % word, tok.line)
        return (m.group(1) is not None, m.group(2).split("."))

    def if_block(self):
        opener = self.tokens[self.pos]
        self.pos += 1
        branches = [(self.condition(opener), self.block(_IF_STOPS))]
        while True:
            tok = self.closer(opener)
            word = tok.value[0]
            if word == "endif":
                self.no_args(tok)
                self.pos += 1
                return ("if", branches)
            if word == "elif":
                self.pos += 1
                branches.append((self.condition(tok), self.block(_IF_STOPS)))
            else:  # "else"
                self.no_args(tok)
                self.pos += 1
                branches.append((None, self.block(("endif",))))
                tok = self.closer(opener)
                self.no_args(tok)
                self.pos += 1
                return ("if", branches)

    def for_block(self):
        opener = self.tokens[self.pos]
        self.pos += 1
        m = _FOR_RE.fullmatch(opener.value[1])
        if m is None:
            raise TemplateError("malformed 'for' tag", opener.line)
        var, path = m.group(1), m.group(2).split(".")
        body = self.block(_FOR_STOPS)
        tok = self.closer(opener)
        else_body = None
        if tok.value[0] == "else":
            self.no_args(tok)
            self.pos += 1
            else_body = self.block(("endfor",))
            tok = self.closer(opener)
        self.no_args(tok)
        self.pos += 1
        return ("for", var, path, body, else_body)


# ------------------------------------------------------------------ renderer

def _filter(value, filters):
    """Apply filters left to right. Returns (value, safe)."""
    safe = False
    for name, arg in filters:
        if name == "upper":
            value = ("" if value is UNDEFINED else str(value)).upper()
        elif name == "lower":
            value = ("" if value is UNDEFINED else str(value)).lower()
        elif name == "length":
            value = len(value) if isinstance(value, (str, list, tuple, dict)) else 0
        elif name == "join":
            if isinstance(value, (list, tuple)):
                value = arg.join(str(x) for x in value)
        elif name == "default":
            if value is UNDEFINED or value is None or (isinstance(value, str) and value == ""):
                value = arg
        elif name == "safe":
            safe = True
    return value, safe


def _to_text(value):
    if value is UNDEFINED or value is None:
        return ""
    return str(value)


def _escape(s):
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
             .replace("'", "&#x27;"))


class _Renderer(object):
    def __init__(self, context):
        # Scope stack: the context dict is never written to; loops push frames.
        self.frames = [context]

    def resolve(self, path):
        value = UNDEFINED
        first = path[0]
        for frame in reversed(self.frames):
            if first in frame:
                value = frame[first]
                break
        for seg in path[1:]:
            if isinstance(value, dict):
                value = value[seg] if seg in value else UNDEFINED
            elif isinstance(value, (list, tuple)) and seg.isdigit():
                idx = int(seg)
                value = value[idx] if idx < len(value) else UNDEFINED
            else:
                return UNDEFINED
        return value

    def truthy(self, cond):
        negated, path = cond
        value = self.resolve(path)
        truth = False if value is UNDEFINED else bool(value)
        return (not truth) if negated else truth

    def render_nodes(self, nodes, out):
        for node in nodes:
            kind = node[0]
            if kind == "text":
                out.append(node[1])
            elif kind == "var":
                value, safe = _filter(self.resolve(node[1]), node[2])
                text = _to_text(value)
                out.append(text if safe else _escape(text))
            elif kind == "if":
                for cond, body in node[1]:
                    if cond is None or self.truthy(cond):
                        self.render_nodes(body, out)
                        break
            else:  # "for"
                _, var, path, body, else_body = node
                seq = self.resolve(path)
                if isinstance(seq, (dict, list, tuple)):
                    items = list(seq)
                else:
                    items = []
                if not items:
                    if else_body is not None:
                        self.render_nodes(else_body, out)
                    continue
                count = len(items)
                for index, item in enumerate(items):
                    self.frames.append({
                        var: item,
                        "loop": {
                            "index": index + 1,
                            "index0": index,
                            "first": index == 0,
                            "last": index == count - 1,
                            "length": count,
                        },
                    })
                    try:
                        self.render_nodes(body, out)
                    finally:
                        self.frames.pop()


def render(template, context=None):
    """Render ``template`` with ``context``. Syntax errors are raised before any output."""
    if context is None:
        context = {}
    nodes = _Parser(tokenize(template)).parse()
    out = []
    _Renderer(context).render_nodes(nodes, out)
    return "".join(out)

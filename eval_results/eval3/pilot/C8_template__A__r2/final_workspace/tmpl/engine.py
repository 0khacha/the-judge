"""Parser and renderer for the template language."""

import html
import re
from dataclasses import dataclass

from .errors import TemplateError
from .lexer import tokenize

_NAME = r"[A-Za-z_][A-Za-z0-9_]*"
_SEG = r"[A-Za-z0-9_]+"
_NAME_RE = re.compile(_NAME)
_IDENT_RE = re.compile(_NAME)
_PATH_RE = re.compile(_NAME + r"(?:\." + _SEG + r")*")
_INDEX_RE = re.compile(r"[0-9]+")

# filter name -> whether it requires a "string" argument
_FILTERS = {
    "upper": False,
    "lower": False,
    "length": False,
    "join": True,
    "default": True,
    "safe": False,
}
_STRAY_TAGS = ("elif", "else", "endif", "endfor", "endraw")


class _Undefined:
    def __repr__(self):
        return "UNDEFINED"


UNDEFINED = _Undefined()
_MISSING = object()


# ---------------------------------------------------------------- AST

@dataclass
class _Text:
    value: str


@dataclass
class _Output:
    path: tuple
    filters: list


@dataclass
class _If:
    branches: list  # [((negated, path), body_nodes), ...]
    else_body: object  # list of nodes or None


@dataclass
class _For:
    name: str
    path: tuple
    body: list
    else_body: object  # list of nodes or None


# ---------------------------------------------------------------- expression parsing

def _skip(s, pos):
    while pos < len(s) and s[pos].isspace():
        pos += 1
    return pos


def _parse_string(body, pos, line):
    """Parse a double-quoted filter argument starting at `pos`."""
    if pos >= len(body) or body[pos] != '"':
        raise TemplateError("malformed expression: expected a quoted argument", line)
    pos += 1
    chars = []
    n = len(body)
    while pos < n:
        c = body[pos]
        if c == '"':
            return "".join(chars), pos + 1
        if c == "\\" and pos + 1 < n and body[pos + 1] in '"\\':
            chars.append(body[pos + 1])
            pos += 2
            continue
        chars.append(c)
        pos += 1
    raise TemplateError("malformed expression: unterminated string", line)


def _parse_expr(body, line):
    """Parse `path|filter|filter:"arg"` into (path_tuple, [(name, arg), ...])."""
    n = len(body)
    pos = _skip(body, 0)
    m = _PATH_RE.match(body, pos)
    if not m:
        raise TemplateError("malformed expression", line)
    path = tuple(m.group(0).split("."))
    pos = m.end()
    filters = []
    while True:
        pos = _skip(body, pos)
        if pos >= n:
            break
        if body[pos] != "|":
            raise TemplateError("malformed expression", line)
        pos = _skip(body, pos + 1)
        m = _IDENT_RE.match(body, pos)
        if not m:
            raise TemplateError("malformed expression: expected a filter name", line)
        name = m.group(0)
        if name not in _FILTERS:
            raise TemplateError("unknown filter %r" % name, line)
        pos = _skip(body, m.end())
        arg = None
        if pos < n and body[pos] == ":":
            pos = _skip(body, pos + 1)
            arg, pos = _parse_string(body, pos, line)
        if _FILTERS[name] and arg is None:
            raise TemplateError("filter %r requires an argument" % name, line)
        if not _FILTERS[name] and arg is not None:
            raise TemplateError("filter %r takes no argument" % name, line)
        filters.append((name, arg))
    return path, filters


def _keyword(tok):
    words = tok.value.split()
    return words[0] if words else ""


def _parse_cond(tok):
    """Parse the condition of an if/elif tag into (negated, path_tuple)."""
    rest = tok.value.split()[1:]
    if len(rest) == 2 and rest[0] == "not":
        negated, text = True, rest[1]
    elif len(rest) == 1:
        negated, text = False, rest[0]
    else:
        raise TemplateError("malformed '%s' tag" % _keyword(tok), tok.line)
    if not _PATH_RE.fullmatch(text):
        raise TemplateError("malformed '%s' tag" % _keyword(tok), tok.line)
    return negated, tuple(text.split("."))


# ---------------------------------------------------------------- parser

class _Parser:
    def __init__(self, tokens):
        self.toks = tokens
        self.i = 0

    def parse(self):
        nodes, _ = self._nodes(frozenset())
        return nodes

    def _nodes(self, terms):
        """Parse nodes until a tag whose keyword is in `terms`.

        Returns (nodes, terminator_token); the terminator is not consumed.
        The terminator is None when the tokens run out.
        """
        out = []
        toks = self.toks
        while self.i < len(toks):
            tok = toks[self.i]
            if tok.kind == "error":
                raise TemplateError(tok.value, tok.line)
            if tok.kind == "text":
                out.append(_Text(tok.value))
                self.i += 1
            elif tok.kind == "var":
                path, filters = _parse_expr(tok.value, tok.line)
                out.append(_Output(path, filters))
                self.i += 1
            elif tok.kind == "comment":
                self.i += 1
            else:
                words = tok.value.split()
                if not words:
                    raise TemplateError("empty tag", tok.line)
                kw = words[0]
                if kw in ("else", "endif", "endfor") and len(words) != 1:
                    raise TemplateError("malformed '%s' tag" % kw, tok.line)
                if kw in terms:
                    return out, tok
                if kw in _STRAY_TAGS:
                    raise TemplateError("'%s' tag in the wrong place" % kw, tok.line)
                if kw == "if":
                    out.append(self._if(tok))
                elif kw == "for":
                    out.append(self._for(tok))
                elif kw == "raw":
                    out.append(self._raw(tok))
                else:
                    raise TemplateError("unknown tag %r" % kw, tok.line)
        return out, None

    def _if(self, tok):
        branches = []
        cond = _parse_cond(tok)
        self.i += 1
        while True:
            body, term = self._nodes(frozenset({"elif", "else", "endif"}))
            if term is None:
                raise TemplateError("unclosed 'if' block", tok.line)
            branches.append((cond, body))
            kw = _keyword(term)
            if kw == "elif":
                cond = _parse_cond(term)
                self.i += 1
                continue
            self.i += 1  # else or endif
            else_body = None
            if kw == "else":
                else_body, term = self._nodes(frozenset({"endif"}))
                if term is None:
                    raise TemplateError("unclosed 'if' block", tok.line)
                self.i += 1  # endif
            return _If(branches, else_body)

    def _for(self, tok):
        words = tok.value.split()
        if (
            len(words) != 4
            or words[2] != "in"
            or not _NAME_RE.fullmatch(words[1])
            or not _PATH_RE.fullmatch(words[3])
        ):
            raise TemplateError("malformed 'for' tag", tok.line)
        self.i += 1
        body, term = self._nodes(frozenset({"else", "endfor"}))
        if term is None:
            raise TemplateError("unclosed 'for' block", tok.line)
        else_body = None
        if _keyword(term) == "else":
            self.i += 1
            else_body, term = self._nodes(frozenset({"endfor"}))
            if term is None:
                raise TemplateError("unclosed 'for' block", tok.line)
        self.i += 1  # endfor
        return _For(words[1], tuple(words[3].split(".")), body, else_body)

    def _raw(self, tok):
        if len(tok.value.split()) != 1:
            raise TemplateError("malformed 'raw' tag", tok.line)
        self.i += 1
        if self.i >= len(self.toks):
            raise TemplateError("unclosed 'raw' block", tok.line)
        content = self.toks[self.i]
        if content.kind == "error":
            raise TemplateError(content.value, content.line)
        self.i += 1
        self.i += 1  # endraw tag, always present after a raw content token
        return _Text(content.value)


# ---------------------------------------------------------------- rendering

def _getseg(value, seg):
    if isinstance(value, dict):
        return value[seg] if seg in value else UNDEFINED
    if isinstance(value, (list, tuple)):
        if _INDEX_RE.fullmatch(seg) and int(seg) < len(value):
            return value[int(seg)]
    return UNDEFINED


def _lookup(env, path):
    value = env.get(path[0], UNDEFINED)
    for seg in path[1:]:
        if value is UNDEFINED:
            break
        value = _getseg(value, seg)
    return value


def _apply_filters(value, filters):
    safe = False
    for name, arg in filters:
        if name == "upper":
            value = "" if value is UNDEFINED else str(value).upper()
        elif name == "lower":
            value = "" if value is UNDEFINED else str(value).lower()
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


def _restore(env, key, saved):
    if saved is _MISSING:
        env.pop(key, None)
    else:
        env[key] = saved


def _render(nodes, env, out):
    for node in nodes:
        if isinstance(node, _Text):
            out.append(node.value)
        elif isinstance(node, _Output):
            value, safe = _apply_filters(_lookup(env, node.path), node.filters)
            text = "" if value is UNDEFINED or value is None else str(value)
            out.append(text if safe else html.escape(text, quote=True))
        elif isinstance(node, _If):
            for (negated, path), body in node.branches:
                value = _lookup(env, path)
                truth = value is not UNDEFINED and bool(value)
                if negated:
                    truth = not truth
                if truth:
                    _render(body, env, out)
                    break
            else:
                if node.else_body is not None:
                    _render(node.else_body, env, out)
        elif isinstance(node, _For):
            seq = _lookup(env, node.path)
            items = list(seq) if isinstance(seq, (list, tuple, dict)) else []
            if not items:
                if node.else_body is not None:
                    _render(node.else_body, env, out)
                continue
            saved_var = env.get(node.name, _MISSING)
            saved_loop = env.get("loop", _MISSING)
            length = len(items)
            try:
                for i, item in enumerate(items):
                    env[node.name] = item
                    env["loop"] = {
                        "index": i + 1,
                        "index0": i,
                        "first": i == 0,
                        "last": i == length - 1,
                        "length": length,
                    }
                    _render(node.body, env, out)
            finally:
                _restore(env, node.name, saved_var)
                _restore(env, "loop", saved_loop)


def render(template, context=None):
    """Render `template` with `context` (a dict). The context is not modified."""
    if context is None:
        context = {}
    nodes = _Parser(tokenize(template)).parse()
    env = dict(context)
    out = []
    _render(nodes, env, out)
    return "".join(out)

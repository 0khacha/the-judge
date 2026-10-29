"""Tokenizer for the template language.

Produces a flat list of tokens:

* ``TEXT``  - literal text (value: str; always emitted, possibly empty)
* ``VAR``   - the inside of ``{{ ... }}`` (value: str, line)
* ``TAG``   - the inside of ``{% ... %}`` split as ``(word, rest)`` (line)

Comments and the contents of ``raw`` blocks are handled here as well:
comments produce no token, raw content becomes a ``TEXT`` token.
Whitespace-control markers are applied while lexing.
"""

import re

from .errors import TemplateError

TEXT = "text"
VAR = "var"
TAG = "tag"

_OPEN_RE = re.compile(r"\{[{%#]")
_RAW_OPEN_RE = re.compile(r"\{%(-?)\s*([A-Za-z_]*)")
_KNOWN_TAGS = ("if", "elif", "else", "endif", "for", "endfor", "raw", "endraw")
_NO_ARG_TAGS = ("else", "endif", "endfor", "endraw")


class Token(object):
    __slots__ = ("kind", "value", "line")

    def __init__(self, kind, value, line=None):
        self.kind = kind
        self.value = value
        self.line = line


def _find_close(src, start, close):
    """Index of ``close`` outside double-quoted strings, or -1."""
    i = start
    n = len(src)
    in_str = False
    while i < n:
        c = src[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif src.startswith(close, i):
            return i
        i += 1
    return -1


class _Lexer(object):
    def __init__(self, src):
        self.src = src
        self.tokens = []
        self.strip_next = False

    def line_at(self, pos):
        return self.src.count("\n", 0, pos) + 1

    def text(self, value):
        # Always emit a TEXT token (even when empty) so that whitespace
        # control only ever affects text that is directly adjacent to a tag.
        if self.strip_next:
            value = value.lstrip()
            self.strip_next = False
        self.tokens.append(Token(TEXT, value))

    def trim(self, left, right):
        if left and self.tokens and self.tokens[-1].kind == TEXT:
            self.tokens[-1].value = self.tokens[-1].value.rstrip()
        self.strip_next = right

    def run(self):
        src = self.src
        pos = 0
        while True:
            m = _OPEN_RE.search(src, pos)
            if m is None:
                self.text(src[pos:])
                return self.tokens
            self.text(src[pos:m.start()])
            kind = m.group()[1]
            line = self.line_at(m.start())
            body = m.end()
            left = src.startswith("-", body)
            if left:
                body += 1
            if kind == "#":
                close = src.find("#}", body)
            else:
                close = _find_close(src, body, "}}" if kind == "{" else "%}")
            if close < 0:
                raise TemplateError("unclosed '%s' delimiter" % m.group(), line)
            content = src[body:close]
            end = close + 2
            right = content.endswith("-")
            if right:
                content = content[:-1]

            if kind == "{":
                if not content.strip():
                    raise TemplateError("empty variable tag", line)
                self.trim(left, right)
                self.tokens.append(Token(VAR, content, line))
            elif kind == "#":
                self.trim(left, right)
            else:
                end = self.tag(content, line, left, right, end)
            pos = end

    def tag(self, content, line, left, right, end):
        parts = content.split(None, 1)
        if not parts:
            raise TemplateError("empty tag", line)
        word = parts[0]
        rest = parts[1].strip() if len(parts) > 1 else ""
        if word == "raw":
            if rest:
                raise TemplateError("malformed 'raw' tag", line)
            self.trim(left, right)
            return self.raw_block(end, line)
        if word not in _KNOWN_TAGS:
            raise TemplateError("unknown tag '%s'" % word, line)
        if word in _NO_ARG_TAGS and rest:
            raise TemplateError("malformed '%s' tag" % word, line)
        self.trim(left, right)
        self.tokens.append(Token(TAG, (word, rest), line))
        return end

    def raw_block(self, start, raw_line):
        """Lex verbatim content from ``start`` up to the matching endraw."""
        src = self.src
        p = start
        while True:
            k = src.find("{%", p)
            if k < 0:
                raise TemplateError("unclosed 'raw' block", raw_line)
            m = _RAW_OPEN_RE.match(src, k)
            if m.group(2) != "endraw":
                p = k + 2
                continue
            line = self.line_at(k)
            close = src.find("%}", k + 2)
            if close < 0:
                raise TemplateError("unclosed '{%' delimiter", line)
            inner = src[k + 2:close]
            left = m.group(1) == "-"
            right = inner.endswith("-")
            body = inner[1 if left else 0:len(inner) - 1 if right else len(inner)]
            if body.strip() != "endraw":
                raise TemplateError("malformed 'endraw' tag", line)
            self.text(src[start:k])
            self.trim(left, right)
            return close + 2


def tokenize(src):
    """Split template source into tokens. Raises TemplateError on lexical errors."""
    return _Lexer(src).run()

"""Tokenizer for the template language.

The lexer never raises. Lexical problems (a delimiter without its closing
delimiter, a raw block that is never closed, a malformed endraw) are emitted
as an "error" token, and the parser raises it when it reaches it, so errors
are reported in document order.
"""

import bisect
import re
from dataclasses import dataclass


@dataclass
class Token:
    kind: str  # "text", "var", "tag", "comment" or "error"
    value: str
    line: int
    ltrim: bool = False  # "{{-", "{%-", "{#-": strip whitespace before the tag
    rtrim: bool = False  # "-}}", "-%}", "-#}": strip whitespace after the tag


_OPENER = re.compile(r"\{[{%#]")
_CLOSERS = {"{": "}}", "%": "%}", "#": "#}"}


def _line_index(src):
    newlines = [m.start() for m in re.finditer("\n", src)]

    def line_of(pos):
        return bisect.bisect_left(newlines, pos) + 1

    return line_of


def _find_var_close(src, i):
    """Index of the '}}' that closes a variable tag, ignoring quoted strings."""
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
        elif c == "}" and src.startswith("}}", i):
            return i
        i += 1
    return -1


def _read_tag(src, start, closer):
    """Read a delimited tag opened at `start`.

    Returns (body, ltrim, rtrim, end) or None if the closing delimiter is missing.
    """
    body_start = start + 2
    ltrim = src.startswith("-", body_start)
    if ltrim:
        body_start += 1
    if closer == "}}":
        close = _find_var_close(src, body_start)
    else:
        close = src.find(closer, body_start)
    if close < 0:
        return None
    rtrim = close - 1 >= body_start and src[close - 1] == "-"
    body = src[body_start:close - 1 if rtrim else close]
    return body, ltrim, rtrim, close + len(closer)


def _read_raw(src, pos, line, line_of):
    """Read the content of a raw block; `pos` is just after the raw opening tag.

    Returns (tokens, end). `end` is None when the block is not closed or the
    endraw tag is malformed; the tokens then end with an error token.
    """
    search = pos
    while True:
        q = src.find("{%", search)
        if q < 0:
            break
        e = src.find("%}", q + 2)
        if e < 0:
            break
        inner = src[q + 2:e]
        ltrim = inner.startswith("-")
        if ltrim:
            inner = inner[1:]
        rtrim = inner.endswith("-")
        if rtrim:
            inner = inner[:-1]
        words = inner.split()
        if words and words[0] == "endraw":
            if len(words) != 1:
                return [Token("error", "malformed 'endraw' tag", line_of(q))], None
            return [
                Token("text", src[pos:q], line),
                Token("tag", "endraw", line_of(q), ltrim, rtrim),
            ], e + 2
        search = q + 2
    return [Token("error", "'raw' block is never closed", line)], None


def _apply_trim(tokens):
    """Apply whitespace-control markers to the literal text next to them."""
    for i, tok in enumerate(tokens):
        if tok.kind == "error":
            continue
        if tok.ltrim and i > 0 and tokens[i - 1].kind == "text":
            tokens[i - 1].value = tokens[i - 1].value.rstrip()
        if tok.rtrim and i + 1 < len(tokens) and tokens[i + 1].kind == "text":
            tokens[i + 1].value = tokens[i + 1].value.lstrip()
    return tokens


def tokenize(src):
    line_of = _line_index(src)
    tokens = []
    pos = 0
    while True:
        m = _OPENER.search(src, pos)
        if m is None:
            break
        start = m.start()
        if start > pos:
            tokens.append(Token("text", src[pos:start], line_of(pos)))
        kind = src[start + 1]
        line = line_of(start)
        found = _read_tag(src, start, _CLOSERS[kind])
        if found is None:
            tokens.append(Token("error", "missing closing delimiter %r" % _CLOSERS[kind], line))
            return _apply_trim(tokens)
        body, ltrim, rtrim, pos = found
        if kind == "#":
            tokens.append(Token("comment", "", line, ltrim, rtrim))
        elif kind == "{":
            tokens.append(Token("var", body, line, ltrim, rtrim))
        else:
            tokens.append(Token("tag", body, line, ltrim, rtrim))
            words = body.split()
            if words and words[0] == "raw":
                raw_tokens, end = _read_raw(src, pos, line, line_of)
                tokens.extend(raw_tokens)
                if end is None:
                    return _apply_trim(tokens)
                pos = end
    if pos < len(src):
        tokens.append(Token("text", src[pos:], line_of(pos)))
    return _apply_trim(tokens)

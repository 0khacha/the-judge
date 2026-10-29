"""Turn tokens into a tree of nodes."""
import re
from dataclasses import dataclass
from typing import Any

from .errors import TemplateError
from .filters import FILTER_ARG_TYPES, FILTER_ARITY, FILTERS
from .lexer import tokenize
from .nodes import Branch, Cond, Filter, For, If, Text, Var

IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PATH_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)*$")
FILTER_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(?:\((.*)\))?$", re.S)
COND_RE = re.compile(r"^([^=!\s]+)(?:\s*(==|!=)\s*(.+))?$", re.S)
LITERAL_RE = re.compile(r""""([^"]*)"|'([^']*)'|(-?[0-9]+)""")


def parse_literal(text: str) -> Any:
    """Value of a quoted string or integer literal. Raises ValueError otherwise."""
    m = LITERAL_RE.fullmatch(text)
    if not m:
        raise ValueError(text)
    if m.group(3) is not None:
        return int(m.group(3))
    return m.group(1) if m.group(1) is not None else m.group(2)


def split_outside_quotes(text, sep, line):
    """Split on sep, ignoring separators inside '...' or "..." literals."""
    parts, cur, quote = [], [], None
    for ch in text:
        if quote:
            cur.append(ch)
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            cur.append(ch)
        elif ch == sep:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if quote:
        raise TemplateError("line %d: unterminated string in %r" % (line, text))
    parts.append("".join(cur))
    return parts


def parse_filter(text, line):
    s = text.strip()
    m = FILTER_RE.match(s)
    if not m:
        raise TemplateError("line %d: bad filter %r" % (line, s))
    name, inner = m.group(1), m.group(2)
    if name not in FILTERS:
        raise TemplateError("line %d: unknown filter %r" % (line, name))
    args = []
    if inner is not None and inner.strip():
        for piece in split_outside_quotes(inner, ",", line):
            try:
                args.append(parse_literal(piece.strip()))
            except ValueError:
                raise TemplateError("line %d: malformed argument %r for filter %s"
                                    % (line, piece.strip(), name)) from None
    if len(args) != FILTER_ARITY[name]:
        raise TemplateError("line %d: filter %s takes %d argument(s), got %d"
                            % (line, name, FILTER_ARITY[name], len(args)))
    if name in FILTER_ARG_TYPES and not isinstance(args[0], FILTER_ARG_TYPES[name]):
        raise TemplateError("line %d: filter %s needs a %s argument"
                            % (line, name, FILTER_ARG_TYPES[name].__name__))
    return Filter(name, args, line)


def parse_var(text, line):
    pieces = split_outside_quotes(text, "|", line)
    path = pieces[0].strip()
    if not PATH_RE.match(path):
        raise TemplateError("line %d: bad variable %r" % (line, path))
    filters = [parse_filter(p, line) for p in pieces[1:]]
    return Var(path, filters, line)


def parse_cond(text, line):
    s = text.strip()
    negated = False
    m = re.match(r"^not\s+(.+)$", s, re.S)
    if m:
        negated = True
        s = m.group(1).strip()
    m = COND_RE.match(s)
    if not m or not PATH_RE.match(m.group(1)) or m.group(1) == "not":
        raise TemplateError("line %d: bad condition %r" % (line, text.strip()))
    path, op, lit = m.group(1), m.group(2), m.group(3)
    if op is None:
        return Cond(path, negated)
    if op == "!=" and negated:
        raise TemplateError("line %d: bad condition %r (use 'not path == LITERAL')"
                            % (line, text.strip()))
    try:
        literal = parse_literal(lit.strip())
    except ValueError:
        raise TemplateError("line %d: bad literal %r in condition" % (line, lit.strip())) from None
    return Cond(path, negated, op, literal)


@dataclass
class _Open:
    kind: str                 # "for" or "if"
    node: Any                 # For or If
    parent: list              # body to return to after the block
    line: int


def parse(source):
    root = []
    body = root
    stack = []                # open blocks, innermost last
    for kind, text, line in tokenize(source):
        if kind == "text":
            body.append(Text(text))
        elif kind == "var":
            body.append(parse_var(text, line))
        else:
            words = text.split()
            keyword = words[0] if words else ""
            rest = text.strip()[len(keyword):]
            if keyword == "for":
                if len(words) != 4 or words[2] != "in" or not IDENT_RE.match(words[1]) \
                        or not PATH_RE.match(words[3]):
                    raise TemplateError("line %d: bad for tag %r" % (line, text))
                node = For(words[1], words[3], [], line)
                body.append(node)
                stack.append(_Open("for", node, body, line))
                body = node.body
            elif words == ["endfor"]:
                if not stack:
                    raise TemplateError("line %d: endfor without for" % line)
                top = stack[-1]
                if top.kind != "for":
                    raise TemplateError("line %d: endfor closes an open if" % line)
                stack.pop()
                body = top.parent
            elif keyword == "if":
                node = If([], None, line)
                branch = Branch(parse_cond(rest, line), [], line)
                node.branches.append(branch)
                body.append(node)
                stack.append(_Open("if", node, body, line))
                body = branch.body
            elif keyword == "elif":
                if not stack or stack[-1].kind != "if":
                    raise TemplateError("line %d: elif without if" % line)
                node = stack[-1].node
                if node.else_body is not None:
                    raise TemplateError("line %d: elif after else" % line)
                branch = Branch(parse_cond(rest, line), [], line)
                node.branches.append(branch)
                body = branch.body
            elif words == ["else"]:
                if not stack or stack[-1].kind != "if":
                    raise TemplateError("line %d: else without if" % line)
                node = stack[-1].node
                if node.else_body is not None:
                    raise TemplateError("line %d: second else" % line)
                node.else_body = []
                body = node.else_body
            elif words == ["endif"]:
                if not stack:
                    raise TemplateError("line %d: endif without if" % line)
                top = stack[-1]
                if top.kind != "if":
                    raise TemplateError("line %d: endif closes an open for" % line)
                stack.pop()
                body = top.parent
            else:
                raise TemplateError("line %d: unknown tag %r" % (line, text))
    if stack:
        top = stack[-1]
        raise TemplateError("line %d: unclosed %s" % (top.line, top.kind))
    return root

"""Turn tokens into a tree of nodes."""
import re

from .errors import TemplateError
from .filters import ARITY, FILTERS
from .lexer import tokenize
from .nodes import Cond, For, If, Text, Var

IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PATH_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)*$")
FILTER_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(?:\((.*)\))?$", re.S)
LITERAL_RE = re.compile(r"""^(?:"([^"]*)"|'([^']*)'|(-?\d+))$""")
COND_RE = re.compile(r"""^(not\s+)?([A-Za-z_][A-Za-z0-9_.]*)(?:\s*(==|!=)\s*(.+))?$""", re.S)


def split_unquoted(text, sep):
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
        raise ValueError("unterminated string")
    parts.append("".join(cur))
    return parts


def parse_literal(text, line):
    m = LITERAL_RE.match(text.strip())
    if not m:
        raise TemplateError("line %d: bad literal %r" % (line, text.strip()))
    if m.group(3) is not None:
        return int(m.group(3))
    return m.group(1) if m.group(1) is not None else m.group(2)


def parse_filter(text, line):
    m = FILTER_RE.match(text.strip())
    if not m:
        raise TemplateError("line %d: bad filter %r" % (line, text.strip()))
    name, raw = m.group(1), m.group(2)
    if name not in FILTERS:
        raise TemplateError("line %d: unknown filter %r" % (line, name))
    args = []
    if raw is not None and raw.strip():
        try:
            pieces = split_unquoted(raw, ",")
        except ValueError:
            raise TemplateError("line %d: unterminated string in filter %r" % (line, name))
        args = [parse_literal(p, line) for p in pieces]
    if len(args) != ARITY[name]:
        raise TemplateError("line %d: filter %r takes %d argument(s)" % (line, name, ARITY[name]))
    return (name, args)


def parse_var(text, line):
    try:
        parts = [p.strip() for p in split_unquoted(text, "|")]
    except ValueError:
        raise TemplateError("line %d: unterminated string" % line)
    path = parts[0]
    if not PATH_RE.match(path):
        raise TemplateError("line %d: bad variable %r" % (line, path))
    return Var(path, [parse_filter(p, line) for p in parts[1:]], line)


def parse_cond(text, line):
    m = COND_RE.match(text.strip())
    if not m:
        raise TemplateError("line %d: bad condition %r" % (line, text.strip()))
    negate, path, op, lit = m.groups()
    if not PATH_RE.match(path):
        raise TemplateError("line %d: bad condition %r" % (line, text.strip()))
    literal = parse_literal(lit, line) if op else None
    return Cond(path, op, literal, bool(negate))


def parse(source):
    root = []
    body = root
    stack = []              # (open node, enclosing body)
    for kind, text, line in tokenize(source):
        if kind == "text":
            body.append(Text(text))
        elif kind == "var":
            body.append(parse_var(text, line))
            continue
        else:
            words = text.split()
            head = words[0] if words else ""
            if head == "for":
                if len(words) != 4 or words[2] != "in" or not IDENT_RE.match(words[1]) \
                        or not PATH_RE.match(words[3]):
                    raise TemplateError("line %d: bad for tag %r" % (line, text))
                node = For(words[1], words[3], [], line)
                body.append(node)
                stack.append((node, body))
                body = node.body
            elif head == "if":
                node = If([], line)
                cond = parse_cond(text[2:], line)
                node.branches.append((cond, []))
                body.append(node)
                stack.append((node, body))
                body = node.branches[-1][1]
            elif head in ("elif", "else"):
                if not stack or not isinstance(stack[-1][0], If):
                    raise TemplateError("line %d: %s without if" % (line, head))
                node = stack[-1][0]
                if node.has_else:
                    raise TemplateError("line %d: %s after else" % (line, head))
                if head == "elif":
                    node.branches.append((parse_cond(text[4:], line), []))
                else:
                    if len(words) != 1:
                        raise TemplateError("line %d: bad else tag" % line)
                    node.has_else = True
                    node.branches.append((None, []))
                body = node.branches[-1][1]
            elif words in (["endfor"], ["endif"]):
                want = For if head == "endfor" else If
                if not stack:
                    raise TemplateError("line %d: %s without %s" % (line, head, head[3:]))
                if not isinstance(stack[-1][0], want):
                    raise TemplateError("line %d: %s does not match open block from line %d"
                                        % (line, head, stack[-1][0].line))
                _, body = stack.pop()
            else:
                raise TemplateError("line %d: unknown tag %r" % (line, text))
    if stack:
        node = stack[-1][0]
        raise TemplateError("line %d: unclosed %s" % (node.line, "for" if isinstance(node, For) else "if"))
    return root

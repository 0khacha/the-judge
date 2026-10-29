"""Turn tokens into a tree of nodes."""
import re

from .errors import TemplateError
from .filters import FILTERS
from .lexer import tokenize
from .nodes import Cond, For, If, Text, Var

IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PATH_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)*$")

_PATH = r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)*"
_LITERAL = r"\"[^\"]*\"|'[^']*'|-?[0-9]+"
FILTER_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*(?:\((.*)\))?", re.S)
LITERAL_RE = re.compile(r"\"([^\"]*)\"|'([^']*)'|(-?[0-9]+)")
COND_RE = re.compile(r"(not\s+)?(%s)(?:\s*(==|!=)\s*(%s))?" % (_PATH, _LITERAL))
BLOCK_HEAD_RE = re.compile(r"(if|elif)(?:\s+(.*))?", re.S)


def _split_outside_quotes(text, sep, line):
    """Split on sep, ignoring separators inside '...' or \"...\" literals."""
    parts = []
    cur = []
    quote = None
    for ch in text:
        if quote:
            if ch == quote:
                quote = None
            cur.append(ch)
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


def _parse_args(raw, line):
    if not raw.strip():
        return []
    args = []
    for piece in _split_outside_quotes(raw, ",", line):
        piece = piece.strip()
        m = LITERAL_RE.fullmatch(piece)
        if not m:
            raise TemplateError("line %d: malformed argument %r" % (line, piece))
        if m.group(3) is not None:
            args.append(int(m.group(3)))
        elif m.group(1) is not None:
            args.append(m.group(1))
        else:
            args.append(m.group(2))
    return args


def parse_filter(segment, line):
    seg = segment.strip()
    m = FILTER_RE.fullmatch(seg)
    if not m:
        raise TemplateError("line %d: bad filter %r" % (line, seg))
    name, raw = m.group(1), m.group(2)
    if name not in FILTERS:
        raise TemplateError("line %d: unknown filter %r" % (line, name))
    args = _parse_args(raw or "", line)
    arity = FILTERS[name][1]
    if len(args) != arity:
        raise TemplateError("line %d: filter %s takes %d argument(s), got %d"
                            % (line, name, arity, len(args)))
    if name == "truncate":
        if not isinstance(args[0], int):
            raise TemplateError("line %d: truncate needs an integer" % line)
        if args[0] < 0:
            raise TemplateError("line %d: truncate length must not be negative" % line)
    return (name, args)


def parse_var(text, line):
    parts = _split_outside_quotes(text, "|", line)
    path = parts[0].strip()
    if not PATH_RE.match(path):
        raise TemplateError("line %d: bad variable %r" % (line, path))
    filters = [parse_filter(p, line) for p in parts[1:]]
    return Var(path, filters, line)


def parse_cond(text, line):
    m = COND_RE.fullmatch(text.strip())
    if not m or (m.group(1) and m.group(3) == "!="):
        raise TemplateError("line %d: bad condition %r" % (line, text.strip()))
    negated = m.group(1) is not None
    path, op, lit = m.group(2), m.group(3), m.group(4)
    value = None
    if lit is not None:
        value = lit[1:-1] if lit[0] in "\"'" else int(lit)
    return Cond(negated, path, op, value)


class _Open:
    """A block that has been opened and not yet closed."""

    def __init__(self, kind, node, parent, line):
        self.kind = kind
        self.node = node
        self.parent = parent      # body that the block itself belongs to
        self.line = line


def parse(source):
    root = []
    body = root
    stack = []
    for kind, text, line in tokenize(source):
        if kind == "text":
            body.append(Text(text))
            continue
        if kind == "var":
            body.append(parse_var(text, line))
            continue

        words = text.split()
        head = words[0] if words else ""
        if head == "for":
            if len(words) != 4 or words[2] != "in" or not IDENT_RE.match(words[1]) \
                    or not PATH_RE.match(words[3]):
                raise TemplateError("line %d: bad for tag %r" % (line, text))
            node = For(words[1], words[3], [], line)
            body.append(node)
            stack.append(_Open("for", node, body, line))
            body = node.body
        elif head == "if":
            m = BLOCK_HEAD_RE.fullmatch(text)
            if not m or not m.group(2):
                raise TemplateError("line %d: bad condition in %r" % (line, text))
            node = If([], None, line)
            branch = []
            node.branches.append((parse_cond(m.group(2), line), branch))
            body.append(node)
            stack.append(_Open("if", node, body, line))
            body = branch
        elif head == "elif":
            if not stack or stack[-1].kind != "if":
                raise TemplateError("line %d: elif without if" % line)
            node = stack[-1].node
            if node.else_body is not None:
                raise TemplateError("line %d: elif after else" % line)
            m = BLOCK_HEAD_RE.fullmatch(text)
            if not m or not m.group(2):
                raise TemplateError("line %d: bad condition in %r" % (line, text))
            branch = []
            node.branches.append((parse_cond(m.group(2), line), branch))
            body = branch
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
            if stack[-1].kind != "if":
                raise TemplateError("line %d: endif closes an open for" % line)
            body = stack.pop().parent
        elif words == ["endfor"]:
            if not stack:
                raise TemplateError("line %d: endfor without for" % line)
            if stack[-1].kind != "for":
                raise TemplateError("line %d: endfor closes an open if" % line)
            body = stack.pop().parent
        else:
            raise TemplateError("line %d: unknown tag %r" % (line, text))
    if stack:
        open_block = stack[-1]
        raise TemplateError("line %d: unclosed %s" % (open_block.line, open_block.kind))
    return root

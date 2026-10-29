"""Turn tokens into a tree of nodes."""
import re

from .errors import TemplateError
from .filters import FILTERS
from .lexer import tokenize
from .nodes import For, Text, Var

IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PATH_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)*$")


def parse_var(text, line):
    parts = [p.strip() for p in text.split("|")]
    path, filters = parts[0], parts[1:]
    if not PATH_RE.match(path):
        raise TemplateError("line %d: bad variable %r" % (line, path))
    for name in filters:
        if name not in FILTERS:
            raise TemplateError("line %d: unknown filter %r" % (line, name))
    return Var(path, filters, line)


def parse(source):
    root = []
    body = root
    stack = []              # (open node, enclosing body)
    for kind, text, line in tokenize(source):
        if kind == "text":
            body.append(Text(text))
        elif kind == "var":
            body.append(parse_var(text, line))
        else:
            words = text.split()
            if words and words[0] == "for":
                if len(words) != 4 or words[2] != "in" or not IDENT_RE.match(words[1]) \
                        or not PATH_RE.match(words[3]):
                    raise TemplateError("line %d: bad for tag %r" % (line, text))
                node = For(words[1], words[3], [], line)
                body.append(node)
                stack.append((node, body))
                body = node.body
            elif words == ["endfor"]:
                if not stack:
                    raise TemplateError("line %d: endfor without for" % line)
                _, body = stack.pop()
            else:
                raise TemplateError("line %d: unknown tag %r" % (line, text))
    if stack:
        raise TemplateError("line %d: unclosed for" % stack[-1][0].line)
    return root

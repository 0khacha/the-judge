import re
from collections import namedtuple

from exprlib.errors import EvalError

Token = namedtuple("Token", "kind value")

_TOKEN_RE = re.compile(r"\s*(?:(\d+(?:\.\d+)?)|([A-Za-z_]\w*)|(\*\*|[-+*/])|(\()|(\)))")


def tokenize(text):
    """Return a list of Token(kind, value). kinds: num, name, op, lparen, rparen.

    num values are int (no dot) or float. Raises EvalError on illegal characters.
    """
    tokens = []
    pos = 0
    text = text.rstrip()
    while pos < len(text):
        m = _TOKEN_RE.match(text, pos)
        if not m:
            raise EvalError("unexpected character at %d" % pos)
        num, name, op, lp, rp = m.groups()
        if num is not None:
            tokens.append(Token("num", float(num) if "." in num else int(num)))
        elif name is not None:
            tokens.append(Token("name", name))
        elif op is not None:
            tokens.append(Token("op", op))
        elif lp is not None:
            tokens.append(Token("lparen", "("))
        else:
            tokens.append(Token("rparen", ")"))
        pos = m.end()
    return tokens

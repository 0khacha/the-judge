"""Split a template into text / variable / block tokens."""
import re

TOKEN_RE = re.compile(r"(\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\})", re.S)


def tokenize(source):
    """Return [(kind, text, line)] with kind in text / var / block. Comments are dropped."""
    tokens = []
    line = 1
    for part in TOKEN_RE.split(source):
        if not part:
            continue
        if part.startswith("{{"):
            tokens.append(("var", part[2:-2].strip(), line))
        elif part.startswith("{%"):
            tokens.append(("block", part[2:-2].strip(), line))
        elif part.startswith("{#"):
            pass
        else:
            tokens.append(("text", part, line))
        line += part.count("\n")
    return tokens

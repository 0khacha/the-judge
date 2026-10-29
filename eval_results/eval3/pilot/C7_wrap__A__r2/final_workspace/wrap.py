"""Unicode-aware greedy text wrapper (standard library only)."""

import re
import unicodedata

_WS_RE = re.compile(r"[ \t\n]+")


def _char_width(ch):
    if unicodedata.category(ch) in ("Mn", "Me"):
        return 0
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 2
    return 1


def display_width(s):
    """Number of terminal columns occupied by ``s``."""
    return sum(_char_width(ch) for ch in s)


def _chunks(word):
    """Split a word into chunks, breaking after qualifying hyphens."""
    chunks = []
    start = 0
    for i, ch in enumerate(word):
        if (
            ch == "-"
            and 0 < i < len(word) - 1
            and word[i - 1].isalnum()
            and word[i + 1].isalnum()
        ):
            chunks.append(word[start:i + 1])
            start = i + 1
    chunks.append(word[start:])
    return chunks


def _tokens(words):
    """Return (chunk, separator) pairs; separator is " " between words, "" at hyphen breaks."""
    tokens = []
    for word in words:
        for k, chunk in enumerate(_chunks(word)):
            tokens.append((chunk, " " if k == 0 else ""))
    return tokens


def _wrap_paragraph(words, width, indent, subsequent_indent):
    first_avail = width - display_width(indent)
    sub_avail = width - display_width(subsequent_indent)

    lines = []
    cur = ""
    cur_w = 0

    def avail():
        return first_avail if not lines else sub_avail

    def flush():
        nonlocal cur, cur_w
        lines.append(cur)
        cur = ""
        cur_w = 0

    def hard_break(chunk):
        nonlocal cur, cur_w
        if cur:
            flush()
        for ch in chunk:
            w = _char_width(ch)
            if w == 0:
                cur += ch
                continue
            if cur_w + w > avail():
                flush()
            cur += ch
            cur_w += w

    for index, (chunk, sep) in enumerate(_tokens(words)):
        cw = display_width(chunk)
        if index == 0 or not cur:
            if cw <= avail():
                cur = chunk
                cur_w = cw
            else:
                hard_break(chunk)
            continue
        sw = display_width(sep)
        if cur_w + sw + cw <= avail():
            cur += sep + chunk
            cur_w += sw + cw
        else:
            flush()
            if cw <= avail():
                cur = chunk
                cur_w = cw
            else:
                hard_break(chunk)

    if cur:
        lines.append(cur)

    out = []
    for i, line in enumerate(lines):
        prefix = indent if i == 0 else subsequent_indent
        out.append(prefix + line)
    return "\n".join(out)


def wrap_text(text, width, indent="", subsequent_indent=""):
    """Wrap ``text`` so every output line has display width <= ``width``."""
    if width - display_width(indent) < 2 or width - display_width(subsequent_indent) < 2:
        raise ValueError("at least 2 columns must remain for text after indentation")

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    paragraphs = []
    current = []
    for line in text.split("\n"):
        if line.strip(" \t") == "":
            if current:
                paragraphs.append(current)
                current = []
        else:
            current.append(line)
    if current:
        paragraphs.append(current)

    rendered = []
    for para_lines in paragraphs:
        words = [w for w in _WS_RE.split("\n".join(para_lines)) if w]
        if not words:
            continue
        rendered.append(_wrap_paragraph(words, width, indent, subsequent_indent))

    return "\n\n".join(rendered)

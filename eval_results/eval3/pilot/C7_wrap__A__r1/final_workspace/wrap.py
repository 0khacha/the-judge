"""Unicode-aware text wrapper. Standard library only."""

import re
import unicodedata

_WHITESPACE_RUN = re.compile(r"[ \t\n]+")


def _char_width(ch):
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 2
    if unicodedata.category(ch) in ("Mn", "Me"):
        return 0
    return 1


def display_width(s):
    """Number of terminal columns occupied by ``s``."""
    return sum(_char_width(ch) for ch in s)


def _split_word(word):
    """Split a word into chunks, breaking right after hyphens between alnum characters."""
    parts = []
    start = 0
    last = len(word) - 1
    for i, ch in enumerate(word):
        if (
            ch == "-"
            and 0 < i < last
            and word[i - 1].isalnum()
            and word[i + 1].isalnum()
        ):
            parts.append(word[start : i + 1])
            start = i + 1
    parts.append(word[start:])
    return parts


def _paragraphs(text):
    """Group non-blank lines into paragraphs; blank lines are separators."""
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
    return paragraphs


class _Filler:
    """Greedy line filler for one paragraph."""

    def __init__(self, width, indent, subsequent_indent):
        self.width = width
        self.indent = indent
        self.subsequent_indent = subsequent_indent
        self.first_avail = width - display_width(indent)
        self.next_avail = width - display_width(subsequent_indent)
        self.lines = []
        self.cur = ""
        self.cur_w = 0

    def _avail(self):
        # The current line's index equals len(self.lines).
        return self.first_avail if not self.lines else self.next_avail

    def _flush(self):
        prefix = self.indent if not self.lines else self.subsequent_indent
        self.lines.append(prefix + self.cur)
        self.cur = ""
        self.cur_w = 0

    def _place(self, chunk):
        """Start a fresh line with ``chunk``, hard-breaking it if too wide."""
        w = display_width(chunk)
        if w <= self._avail():
            self.cur = chunk
            self.cur_w = w
            return
        for ch in chunk:
            cw = _char_width(ch)
            if cw and self.cur and self.cur_w + cw > self._avail():
                self._flush()
            self.cur += ch
            self.cur_w += cw

    def add(self, sep, chunk):
        if not self.cur:
            self._place(chunk)
            return
        candidate = self.cur_w + display_width(sep) + display_width(chunk)
        if candidate <= self._avail():
            self.cur += sep + chunk
            self.cur_w = candidate
            return
        self._flush()
        self._place(chunk)

    def finish(self):
        if self.cur:
            self._flush()
        return "\n".join(self.lines)


def wrap_text(text, width, indent="", subsequent_indent=""):
    """Wrap ``text`` so every output line has display width <= ``width``."""
    if width - display_width(indent) < 2 or width - display_width(subsequent_indent) < 2:
        raise ValueError("at least 2 columns must remain for text")

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    outputs = []
    for para in _paragraphs(text):
        words = [w for w in _WHITESPACE_RUN.split("\n".join(para)) if w]
        if not words:
            continue
        filler = _Filler(width, indent, subsequent_indent)
        for word in words:
            for i, chunk in enumerate(_split_word(word)):
                filler.add(" " if i == 0 else "", chunk)
        outputs.append(filler.finish())
    return "\n\n".join(outputs)

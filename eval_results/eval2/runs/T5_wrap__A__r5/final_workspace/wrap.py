"""Display-width aware text wrapping."""

import unicodedata


def _char_width(ch):
    """Terminal columns used by a single character."""
    if unicodedata.combining(ch) != 0:
        return 0
    if unicodedata.category(ch) in ("Mn", "Me", "Cf"):
        return 0
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 2
    return 1


def display_width(s):
    """Return the number of terminal columns used by ``s``."""
    return sum(_char_width(ch) for ch in s)


def _hard_split(word, width):
    """Split ``word`` into pieces no wider than ``width`` where possible.

    Returns (complete_pieces, last_piece). Zero-width characters never start
    a new piece; a single character wider than ``width`` sits alone.
    """
    complete = []
    piece = ""
    piece_w = 0
    for ch in word:
        cw = _char_width(ch)
        if piece and cw > 0 and piece_w + cw > width:
            complete.append(piece)
            piece = ""
            piece_w = 0
        piece += ch
        piece_w += cw
    return complete, piece


def wrap_text(text, width):
    """Wrap ``text`` into lines of at most ``width`` display columns."""
    if isinstance(width, bool) or not isinstance(width, int) or width < 1:
        raise ValueError("width must be an int >= 1")

    lines = []
    cur = ""
    cur_w = 0

    for word in text.split():
        ww = display_width(word)
        if cur and cur_w + 1 + ww <= width:
            cur += " " + word
            cur_w += 1 + ww
            continue
        if cur:
            lines.append(cur)
            cur = ""
            cur_w = 0
        if ww <= width:
            cur = word
            cur_w = ww
        else:
            complete, last = _hard_split(word, width)
            lines.extend(complete)
            cur = last
            cur_w = display_width(last)

    if cur:
        lines.append(cur)
    return lines

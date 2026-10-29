"""Display-width aware text wrapping."""

import unicodedata


def _char_width(ch):
    """Terminal columns used by a single character (0, 1 or 2)."""
    if unicodedata.combining(ch) != 0 or unicodedata.category(ch) in ("Mn", "Me", "Cf"):
        return 0
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 2
    return 1


def display_width(s):
    """Return the number of terminal columns used by ``s``."""
    return sum(_char_width(ch) for ch in s)


def _validate_width(width):
    if isinstance(width, bool) or not isinstance(width, int) or width < 1:
        raise ValueError(f"width must be an int >= 1, got {width!r}")


def _hard_split(word, width):
    """Split a word that is wider than ``width`` into pieces.

    Returns (complete_lines, final_piece, final_piece_width).
    """
    lines = []
    piece = ""
    piece_w = 0
    for ch in word:
        cw = _char_width(ch)
        # A zero-width char never starts a new piece; a visible char that would
        # overflow closes the current piece (only if the piece holds something visible).
        if piece_w > 0 and piece_w + cw > width:
            lines.append(piece)
            piece = ""
            piece_w = 0
        piece += ch
        piece_w += cw
    return lines, piece, piece_w


def wrap_text(text, width):
    """Greedily wrap ``text`` into lines of at most ``width`` display columns."""
    _validate_width(width)
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
            cur, cur_w = word, ww
            continue
        full, cur, cur_w = _hard_split(word, width)
        lines.extend(full)
    if cur:
        lines.append(cur)
    return lines

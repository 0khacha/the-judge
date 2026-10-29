"""Display-width aware text wrapping."""

import unicodedata


def _char_width(ch):
    if unicodedata.combining(ch) != 0 or unicodedata.category(ch) in ("Mn", "Me", "Cf"):
        return 0
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 2
    return 1


def display_width(s):
    """Return the number of terminal columns used by ``s``."""
    return sum(_char_width(ch) for ch in s)


def _hard_split(word, width):
    """Split ``word`` into pieces of at most ``width`` columns.

    Returns (complete_pieces, final_piece, final_piece_width).
    Zero-width characters never start a new piece.
    """
    complete = []
    piece = ""
    piece_w = 0
    for ch in word:
        cw = _char_width(ch)
        if piece and cw > 0 and piece_w + cw > width:
            complete.append(piece)
            piece = ch
            piece_w = cw
        else:
            piece += ch
            piece_w += cw
    return complete, piece, piece_w


def wrap_text(text, width):
    """Wrap ``text`` into lines of at most ``width`` display columns."""
    if not isinstance(width, int) or isinstance(width, bool) or width < 1:
        raise ValueError("width must be an integer >= 1")

    words = text.split()
    lines = []
    cur = ""
    cur_w = 0

    for word in words:
        ww = display_width(word)
        if ww <= width:
            if cur and cur_w + 1 + ww <= width:
                cur += " " + word
                cur_w += 1 + ww
            else:
                if cur:
                    lines.append(cur)
                cur = word
                cur_w = ww
        else:
            if cur:
                lines.append(cur)
                cur = ""
                cur_w = 0
            complete, cur, cur_w = _hard_split(word, width)
            lines.extend(complete)

    if cur:
        lines.append(cur)
    return lines

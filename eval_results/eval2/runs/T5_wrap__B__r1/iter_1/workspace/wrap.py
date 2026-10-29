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
    """Split one over-wide word into pieces.

    Returns (complete_pieces, final_piece, final_piece_width).
    """
    pieces = []
    piece = ""
    piece_w = 0
    for ch in word:
        cw = _char_width(ch)
        if cw == 0:
            # Zero-width characters stay attached to the preceding character.
            piece += ch
            continue
        if piece and piece_w + cw > width:
            pieces.append(piece)
            piece = ""
            piece_w = 0
        piece += ch
        piece_w += cw
    return pieces, piece, piece_w


def wrap_text(text, width):
    """Wrap ``text`` into lines of at most ``width`` display columns."""
    if isinstance(width, bool) or not isinstance(width, int) or width < 1:
        raise ValueError("width must be an integer >= 1")

    lines = []
    cur = ""
    cur_w = 0
    for word in text.split():
        ww = display_width(word)
        if ww <= width:
            if not cur:
                cur, cur_w = word, ww
            elif cur_w + 1 + ww <= width:
                cur += " " + word
                cur_w += 1 + ww
            else:
                lines.append(cur)
                cur, cur_w = word, ww
        else:
            if cur:
                lines.append(cur)
            pieces, cur, cur_w = _hard_split(word, width)
            lines.extend(pieces)
    if cur:
        lines.append(cur)
    return lines

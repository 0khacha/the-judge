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
    """Split a word wider than ``width`` into pieces.

    Returns (complete_pieces, final_piece, final_piece_width).
    """
    pieces = []
    piece = ""
    piece_w = 0
    for ch in word:
        w = _char_width(ch)
        if w == 0:
            # Zero-width characters attach to the preceding character.
            piece += ch
            continue
        if piece_w + w > width and piece_w > 0:
            pieces.append(piece)
            piece = ch
            piece_w = w
        else:
            piece += ch
            piece_w += w
    return pieces, piece, piece_w


def wrap_text(text, width):
    """Greedily wrap ``text`` into lines of at most ``width`` display columns."""
    if isinstance(width, bool) or not isinstance(width, int):
        raise ValueError("width must be an int")
    if width < 1:
        raise ValueError("width must be >= 1")

    lines = []
    cur = None
    cur_w = 0

    for word in text.split():
        ww = display_width(word)
        if ww > width:
            if cur is not None:
                lines.append(cur)
                cur = None
            pieces, cur, cur_w = _hard_split(word, width)
            lines.extend(pieces)
        elif cur is None:
            cur, cur_w = word, ww
        elif cur_w + 1 + ww <= width:
            cur = cur + " " + word
            cur_w += 1 + ww
        else:
            lines.append(cur)
            cur, cur_w = word, ww

    if cur is not None:
        lines.append(cur)
    return lines

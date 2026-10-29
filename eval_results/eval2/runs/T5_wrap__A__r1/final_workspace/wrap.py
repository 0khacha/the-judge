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

    Returns ``(complete_pieces, final_piece, final_piece_width)``.
    Zero-width characters stay attached to the preceding character.
    """
    pieces = []
    piece = ""
    pw = 0
    for ch in word:
        cw = _char_width(ch)
        # Only break when the current piece already holds visible content;
        # zero-width characters never start a new piece.
        if cw > 0 and pw > 0 and pw + cw > width:
            pieces.append(piece)
            piece = ""
            pw = 0
        piece += ch
        pw += cw
    return pieces, piece, pw


def wrap_text(text, width):
    """Wrap ``text`` into lines of at most ``width`` display columns."""
    if isinstance(width, bool) or not isinstance(width, int) or width < 1:
        raise ValueError("width must be an integer >= 1")

    lines = []
    cur = None  # current line being filled
    cur_w = 0

    for word in text.split():
        ww = display_width(word)
        if cur is not None and cur_w + 1 + ww <= width:
            cur += " " + word
            cur_w += 1 + ww
            continue

        if cur is not None:
            lines.append(cur)
            cur = None

        if ww <= width:
            cur, cur_w = word, ww
        else:
            pieces, cur, cur_w = _hard_split(word, width)
            lines.extend(pieces)

    if cur is not None:
        lines.append(cur)
    return lines

"""Display-width aware text wrapping for terminal output."""

import unicodedata

_ZERO_WIDTH_CATEGORIES = {"Mn", "Me", "Cf"}


def _char_width(ch):
    if unicodedata.combining(ch) != 0 or unicodedata.category(ch) in _ZERO_WIDTH_CATEGORIES:
        return 0
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 2
    return 1


def display_width(s):
    """Return the number of terminal columns used by ``s``."""
    return sum(_char_width(ch) for ch in s)


def _hard_split(word, width):
    """Split ``word`` into pieces that fit ``width``.

    Returns (complete_pieces, last_piece, last_piece_width). The last piece
    is not yet a finished line and may be joined by following words.
    """
    complete = []
    piece = ""
    piece_w = 0
    for ch in word:
        w = _char_width(ch)
        # A zero-width char never starts a new piece; a wide char that is
        # alone on an empty piece is accepted even if it exceeds width.
        if piece and w > 0 and piece_w + w > width:
            complete.append(piece)
            piece = ch
            piece_w = w
        else:
            piece += ch
            piece_w += w
    return complete, piece, piece_w


def wrap_text(text, width):
    """Wrap ``text`` into lines of at most ``width`` display columns."""
    if isinstance(width, bool) or not isinstance(width, int):
        raise ValueError("width must be an int")
    if width < 1:
        raise ValueError("width must be at least 1")

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
            complete, cur, cur_w = _hard_split(word, width)
            lines.extend(complete)

    if cur:
        lines.append(cur)
    return lines

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


def wrap_text(text, width):
    """Wrap ``text`` into lines of at most ``width`` display columns."""
    if isinstance(width, bool) or not isinstance(width, int) or width < 1:
        raise ValueError("width must be an int >= 1")

    lines = []
    current = ""
    cur_w = 0

    for word in text.split():
        ww = display_width(word)

        # Greedy: join the current line if the word fits after one space.
        if current and cur_w + 1 + ww <= width:
            current += " " + word
            cur_w += 1 + ww
            continue

        if current:
            lines.append(current)
            current, cur_w = "", 0

        if ww <= width:
            current, cur_w = word, ww
            continue

        # Word is wider than the line: hard-split character by character.
        piece, pw = "", 0
        for ch in word:
            cw = _char_width(ch)
            # A zero-width char never starts a new piece; a wide char that
            # does not fit ends the current piece.
            if piece and cw and pw + cw > width:
                lines.append(piece)
                piece, pw = "", 0
            piece += ch
            pw += cw
        current, cur_w = piece, pw

    if current:
        lines.append(current)
    return lines

import unicodedata


def _char_width(ch):
    """Terminal columns used by a single character."""
    if unicodedata.combining(ch) != 0 or unicodedata.category(ch) in ("Mn", "Me", "Cf"):
        return 0
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 2
    return 1


def display_width(s):
    """Number of terminal columns used by the string s."""
    return sum(_char_width(ch) for ch in s)


def _hard_split(word, width):
    """Split a word wider than width into pieces.

    Returns (complete_lines, last_piece, last_piece_width). The last piece is
    the still-open current line; it is never empty.
    """
    complete = []
    piece = ""
    piece_w = 0
    for ch in word:
        cw = _char_width(ch)
        if cw == 0:
            # Zero-width characters attach to the preceding character.
            piece += ch
            continue
        if piece_w > 0 and piece_w + cw > width:
            complete.append(piece)
            piece = ch
            piece_w = cw
        else:
            piece += ch
            piece_w += cw
    return complete, piece, piece_w


def wrap_text(text, width):
    """Greedily wrap text into lines of at most width display columns."""
    if isinstance(width, bool) or not isinstance(width, int) or width < 1:
        raise ValueError("width must be an int >= 1")

    words = text.split()
    if not words:
        return []

    lines = []
    cur = ""
    cur_w = 0
    cur_has = False

    for word in words:
        ww = display_width(word)
        if cur_has and cur_w + 1 + ww <= width:
            cur += " " + word
            cur_w += 1 + ww
            continue
        if cur_has:
            lines.append(cur)
            cur = ""
            cur_w = 0
            cur_has = False
        if ww <= width:
            cur = word
            cur_w = ww
            cur_has = True
        else:
            complete, cur, cur_w = _hard_split(word, width)
            lines.extend(complete)
            cur_has = True

    if cur_has:
        lines.append(cur)
    return lines

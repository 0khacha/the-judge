"""Display-width aware text wrapping."""

import unicodedata

_ZERO_CATEGORIES = {"Mn", "Me", "Cf"}


def _char_width(ch):
    if unicodedata.combining(ch) != 0 or unicodedata.category(ch) in _ZERO_CATEGORIES:
        return 0
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 2
    return 1


def display_width(s):
    """Return the number of terminal columns used by ``s``."""
    return sum(_char_width(ch) for ch in s)


def _split_word(word, width):
    """Hard-split a word that is wider than ``width``.

    Returns (complete_pieces, last_piece). Zero-width characters never start
    a new piece; a single over-wide character is placed alone on its piece.
    """
    pieces = []
    current = ""
    current_w = 0
    for ch in word:
        w = _char_width(ch)
        if w == 0:
            # Attach to the preceding character; if there is no current piece
            # yet, it simply starts the piece with zero width.
            current += ch
            continue
        if current and current_w + w > width:
            pieces.append(current)
            current = ch
            current_w = w
        else:
            current += ch
            current_w += w
    return pieces, current


def wrap_text(text, width):
    """Wrap ``text`` into lines of at most ``width`` display columns."""
    if isinstance(width, bool) or not isinstance(width, int) or width < 1:
        raise ValueError("width must be an integer >= 1")

    words = text.split()
    lines = []
    current = ""
    current_w = 0

    def flush():
        nonlocal current, current_w
        if current:
            lines.append(current)
        current = ""
        current_w = 0

    for word in words:
        word_w = display_width(word)
        if word_w > width:
            # Finish the current line, then hard-split the long word.
            flush()
            pieces, last = _split_word(word, width)
            for piece in pieces:
                lines.append(piece)
            current = last
            current_w = display_width(last)
            continue

        if current:
            if current_w + 1 + word_w <= width:
                current += " " + word
                current_w += 1 + word_w
                continue
            flush()
        current = word
        current_w = word_w

    flush()
    return lines

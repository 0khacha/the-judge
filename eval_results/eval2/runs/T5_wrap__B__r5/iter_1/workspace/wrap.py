"""Display-width aware text wrapping."""

import unicodedata

_ZERO_WIDTH_CATEGORIES = frozenset({"Mn", "Me", "Cf"})


def _char_width(ch: str) -> int:
    if unicodedata.combining(ch) != 0 or unicodedata.category(ch) in _ZERO_WIDTH_CATEGORIES:
        return 0
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 2
    return 1


def display_width(s: str) -> int:
    """Return the number of terminal columns used by ``s``."""
    return sum(_char_width(ch) for ch in s)


def _hard_split(word: str, width: int) -> tuple[list[str], str]:
    """Split an over-wide word into pieces.

    Returns (complete pieces, final piece). The final piece may still accept
    following words, so it is returned separately.
    """
    pieces: list[str] = []
    piece = ""
    piece_w = 0
    for ch in word:
        w = _char_width(ch)
        if w == 0:
            # Zero-width characters never start a new piece.
            piece += ch
            continue
        if piece and piece_w + w > width:
            pieces.append(piece)
            piece, piece_w = ch, w
        else:
            piece += ch
            piece_w += w
    return pieces, piece


def wrap_text(text: str, width: int) -> list[str]:
    """Greedily wrap ``text`` so each line is at most ``width`` display columns."""
    if isinstance(width, bool) or not isinstance(width, int) or width < 1:
        raise ValueError(f"width must be an int >= 1, got {width!r}")

    lines: list[str] = []
    cur = ""
    cur_w = 0
    for word in text.split():
        word_w = display_width(word)
        if cur and cur_w + 1 + word_w <= width:
            cur += " " + word
            cur_w += 1 + word_w
            continue
        if cur:
            lines.append(cur)
            cur, cur_w = "", 0
        if word_w <= width:
            cur, cur_w = word, word_w
        else:
            pieces, cur = _hard_split(word, width)
            lines.extend(pieces)
            cur_w = display_width(cur)
    if cur:
        lines.append(cur)
    return lines

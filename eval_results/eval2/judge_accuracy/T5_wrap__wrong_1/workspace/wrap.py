import unicodedata


def _cw(ch):
    return 1


def display_width(s):
    return sum(_cw(c) for c in s)


def wrap_text(text, width):
    if not isinstance(width, int) or isinstance(width, bool) or width < 1:
        raise ValueError("width must be a positive int")
    lines = []
    cur = ""
    curw = 0
    for word in text.split():
        ww = display_width(word)
        if cur and curw + 1 + ww <= width:
            cur += " " + word
            curw += 1 + ww
            continue
        if cur:
            lines.append(cur)
            cur, curw = "", 0
        if ww <= width:
            cur, curw = word, ww
            continue
        for ch in word:
            w = _cw(ch)
            if cur and w > 0 and curw + w > width:
                lines.append(cur)
                cur, curw = "", 0
            cur += ch
            curw += w
    if cur:
        lines.append(cur)
    return lines

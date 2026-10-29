import re
import unicodedata


def _cw(ch):
    if unicodedata.category(ch) in ("Mn", "Me"):
        return 0
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 2
    return 1


def display_width(s):
    return sum(_cw(c) for c in s)


def _chunks(word):
    out = []
    start = 0
    for i, ch in enumerate(word):
        if ch == "-" and 0 < i < len(word) - 1 and word[i - 1].isalnum() and word[i + 1].isalnum():
            out.append(word[start:i + 1])
            start = i + 1
    out.append(word[start:])
    return out


def _wrap_par(words, width, ind, sub):
    out = []
    cur = ""
    cw = 0

    def prefix():
        return ind if not out else sub

    def avail():
        return width - display_width(prefix())

    def flush():
        nonlocal cur, cw
        out.append(prefix() + cur)
        cur = ""
        cw = 0

    for word in words:
        for k, chunk in enumerate(_chunks(word)):
            w = display_width(chunk)
            sep = 0 if (k > 0 or not cur) else 1
            if cw + sep + w <= avail():
                cur += (" " if sep else "") + chunk
                cw += sep + w
                continue
            if cur:
                flush()
            if w <= avail():
                cur = chunk
                cw = w
                continue
            for ch in chunk:
                c = _cw(ch)
                if c > 0 and cw > 0 and cw + c > avail():
                    flush()
                cur += ch
                cw += c
    if cur:
        flush()
    return out


def wrap_text(text, width, indent="", subsequent_indent=""):
    if width - display_width(indent) < 2 or width - display_width(subsequent_indent) < 2:
        raise ValueError("width too small for indents")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    paras = []
    cur = []
    for line in text.split("\n"):
        if line.strip(" \t") == "":
            if cur:
                paras.append(cur)
                cur = []
        else:
            cur.append(line)
    if cur:
        paras.append(cur)
    result = []
    for p in paras:
        words = [w for w in re.split(r"[ \t\n]+", " ".join(p)) if w]
        if words:
            result.append("\n".join(_wrap_par(words, width, indent, subsequent_indent)))
    return "\n\n".join(result)

import re
import unicodedata


def slugify(text, max_length=None):
    if max_length is not None and max_length < 1:
        raise ValueError("max_length must be >= 1")
    s = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    if max_length is None or len(s) <= max_length:
        return s
    if s[max_length] == "-":
        return s[:max_length].strip("-")
    cut = s[:max_length].rfind("-")
    if cut <= 0:
        return s[:max_length]
    return s[:cut]

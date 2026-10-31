import re
import unicodedata


def slugify(text: str, max_length: int | None = None) -> str:
    if max_length is not None and max_length < 1:
        raise ValueError("max_length must be >= 1")
    s = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    if max_length is None or len(s) <= max_length:
        return s
    if s[max_length] == "-":
        return s[:max_length]
    cut = s[:max_length]
    idx = cut.rfind("-")
    if idx > 0:
        return cut[:idx]
    return cut

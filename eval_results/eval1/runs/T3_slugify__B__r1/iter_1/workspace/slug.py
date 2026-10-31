import re
import unicodedata


def slugify(text: str, max_length: int | None = None) -> str:
    if max_length is not None and max_length < 1:
        raise ValueError("max_length must be >= 1")
    norm = unicodedata.normalize("NFKD", text)
    ascii_text = norm.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    if max_length is None or len(slug) <= max_length:
        return slug
    words = slug.split("-")
    out = ""
    for w in words:
        cand = w if not out else out + "-" + w
        if len(cand) > max_length:
            break
        out = cand
    if not out:
        out = words[0][:max_length]
    return out

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
    if len(words[0]) > max_length:
        return words[0][:max_length]
    out = words[0]
    for w in words[1:]:
        if len(out) + 1 + len(w) > max_length:
            break
        out += "-" + w
    return out

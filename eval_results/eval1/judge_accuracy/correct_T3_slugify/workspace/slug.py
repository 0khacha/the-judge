import re
import unicodedata


def slugify(text: str, max_length=None) -> str:
    if max_length is not None and max_length < 1:
        raise ValueError("max_length must be >= 1")
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    if max_length is None or len(slug) <= max_length:
        return slug
    cut = slug[:max_length + 1]
    if "-" in cut:
        return cut[:cut.rindex("-")].rstrip("-")
    return slug[:max_length]

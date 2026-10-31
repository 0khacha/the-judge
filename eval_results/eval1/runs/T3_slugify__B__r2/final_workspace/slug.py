import re
import unicodedata


def slugify(text: str, max_length: int | None = None) -> str:
    if max_length is not None and max_length < 1:
        raise ValueError("max_length must be >= 1")
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", norm.lower()).strip("-")
    if max_length is None or len(slug) <= max_length:
        return slug
    if slug[max_length] == "-":
        return slug[:max_length]
    cut = slug[:max_length].rfind("-")
    if cut <= 0:
        return slug[:max_length]
    return slug[:cut]

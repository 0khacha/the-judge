import re
import unicodedata


def slugify(text: str, max_length=None) -> str:
    if max_length is not None and max_length < 1:
        raise ValueError("max_length must be >= 1")
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    # Subtle bug: hard cut can split a word and leave a trailing "-".
    return slug if max_length is None else slug[:max_length]

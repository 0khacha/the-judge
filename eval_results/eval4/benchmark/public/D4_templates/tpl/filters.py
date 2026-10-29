"""Built-in filters. Each takes the value and returns the new value."""


class SafeStr(str):
    """Text that must not be HTML-escaped again."""


def _upper(value):
    return str(value).upper()


def _lower(value):
    return str(value).lower()


def _title(value):
    return str(value).title()


def _trim(value):
    return str(value).strip()


def _length(value):
    return len(value)


def _safe(value):
    return SafeStr(value)


FILTERS = {
    "upper": _upper,
    "lower": _lower,
    "title": _title,
    "trim": _trim,
    "length": _length,
    "safe": _safe,
}

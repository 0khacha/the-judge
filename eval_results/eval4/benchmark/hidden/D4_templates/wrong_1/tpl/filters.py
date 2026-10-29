"""Built-in filters. Each takes the value (plus literal arguments) and returns the new value."""
from .context import UNDEFINED
from .errors import TemplateError


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


def _default(value, fallback):
    if value is UNDEFINED or value is None:
        return fallback
    return value


def _join(value, sep):
    if not isinstance(value, (list, tuple)):
        raise TemplateError("join needs a list")
    return str(sep).join(str(item) for item in value)


def _truncate(value, n):
    if n < 0:
        raise TemplateError("truncate length must be >= 0")
    text = str(value)
    return text if len(text) <= n else text[:n] + "..."


FILTERS = {
    "upper": _upper,
    "lower": _lower,
    "title": _title,
    "trim": _trim,
    "length": _length,
    "safe": _safe,
    "default": _default,
    "join": _join,
    "truncate": _truncate,
}

ARITY = {"upper": 0, "lower": 0, "title": 0, "trim": 0, "length": 0, "safe": 0,
         "default": 1, "join": 1, "truncate": 1}

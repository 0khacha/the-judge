"""Built-in filters.

Each entry maps a name to (function, number of literal arguments). The function
receives the value followed by the arguments and returns the new value.
Escaping is decided by the renderer: the result is escaped unless the last
filter of the chain is ``safe``.
"""
from .context import UNDEFINED
from .errors import TemplateError


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
    return value


def _default(value, fallback):
    if value is UNDEFINED or value is None:
        return fallback
    return value


def _join(value, sep):
    if not isinstance(value, (list, tuple)):
        raise TemplateError("join needs a list, got %s" % type(value).__name__)
    return str(sep).join(str(item) for item in value)


def _truncate(value, n):
    text = str(value)
    if len(text) <= n:
        return text
    return text[:n] + "..."


FILTERS = {
    "upper": (_upper, 0),
    "lower": (_lower, 0),
    "title": (_title, 0),
    "trim": (_trim, 0),
    "length": (_length, 0),
    "safe": (_safe, 0),
    "default": (_default, 1),
    "join": (_join, 1),
    "truncate": (_truncate, 1),
}

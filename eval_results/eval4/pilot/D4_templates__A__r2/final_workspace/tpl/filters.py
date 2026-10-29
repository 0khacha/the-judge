"""Built-in filters. Each takes the value (and literal arguments) and returns the new value."""
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
    if isinstance(value, SafeStr):
        # a later default must not keep the 'safe' marking
        return str(value)
    return value


def _join(value, sep):
    if not isinstance(value, (list, tuple)):
        raise TemplateError("join needs a list, got %s" % type(value).__name__)
    return sep.join(str(item) for item in value)


def _truncate(value, n):
    if n < 0:
        raise TemplateError("truncate length must not be negative, got %d" % n)
    text = str(value)
    if len(text) <= n:
        return text
    return text[:n] + "..."


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

# number of literal arguments each filter takes
FILTER_ARITY = {
    "upper": 0,
    "lower": 0,
    "title": 0,
    "trim": 0,
    "length": 0,
    "safe": 0,
    "default": 1,
    "join": 1,
    "truncate": 1,
}

# required Python type of literal arguments, where it is not "any"
FILTER_ARG_TYPES = {
    "join": str,
    "truncate": int,
}

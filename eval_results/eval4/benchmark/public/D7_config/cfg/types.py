"""Conversions of resolved strings."""
from .errors import ConfigError

TRUE = {"true", "yes", "on", "1"}
FALSE = {"false", "no", "off", "0"}


def to_int(text, where):
    try:
        return int(text.strip())
    except ValueError:
        raise ConfigError("%s: not an int: %r" % (where, text))


def to_float(text, where):
    try:
        return float(text.strip())
    except ValueError:
        raise ConfigError("%s: not a float: %r" % (where, text))


def to_bool(text, where):
    low = text.strip().lower()
    if low in TRUE:
        return True
    if low in FALSE:
        return False
    raise ConfigError("%s: not a bool: %r" % (where, text))


def to_list(text, where):
    return [part.strip() for part in text.split(",") if part.strip()]

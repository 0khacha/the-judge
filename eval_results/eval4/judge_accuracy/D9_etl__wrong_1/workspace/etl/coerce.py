"""String -> typed value."""
from datetime import date

TRUE = {"true", "yes", "y", "1"}
FALSE = {"false", "no", "n", "0"}
TYPES = ("str", "int", "float", "date", "bool")


def coerce(text, typ):
    text = text.strip()
    if typ == "str":
        return text
    if typ == "int":
        try:
            return int(text)
        except ValueError:
            raise ValueError("not an int: %r" % text)
    if typ == "float":
        try:
            return float(text)
        except ValueError:
            raise ValueError("not a float: %r" % text)
    if typ == "date":
        try:
            return date.fromisoformat(text)
        except ValueError:
            raise ValueError("not a date: %r" % text)
    if typ == "bool":
        low = text.lower()
        if low in TRUE:
            return True
        if low in FALSE:
            return False
        raise ValueError("not a bool: %r" % text)
    raise ValueError("unknown type %r" % typ)

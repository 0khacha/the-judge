"""Variable lookup through a stack of scopes."""


class _Undefined:
    def __repr__(self):
        return "UNDEFINED"

    def __bool__(self):
        return False


UNDEFINED = _Undefined()


def _step(obj, name):
    if isinstance(obj, dict):
        return obj.get(name, UNDEFINED)
    if isinstance(obj, (list, tuple)):
        if name.isdigit() and int(name) < len(obj):
            return obj[int(name)]
        return UNDEFINED
    return getattr(obj, name, UNDEFINED)


def lookup(scopes, path):
    """Resolve a dotted path; innermost scope wins. Returns UNDEFINED when missing."""
    first, *rest = path.split(".")
    value = UNDEFINED
    for scope in reversed(scopes):
        if first in scope:
            value = scope[first]
            break
    for name in rest:
        if value is UNDEFINED or value is None:
            return UNDEFINED
        value = _step(value, name)
    return value

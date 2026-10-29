"""Function result caching on top of Cache."""
import functools

_MISSING = object()


def memoize(cache, key_fn=None, ttl=None):
    """Decorator: cache results keyed by the call arguments (None results are cached too)."""

    def decorate(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if key_fn is not None:
                key = key_fn(*args, **kwargs)
            else:
                key = (fn.__qualname__, args, tuple(sorted(kwargs.items())))
            found = cache.get(key, _MISSING)
            if found is not _MISSING:
                return found
            value = fn(*args, **kwargs)
            cache.put(key, value, ttl)
            return value

        wrapper.cache = cache
        return wrapper

    return decorate

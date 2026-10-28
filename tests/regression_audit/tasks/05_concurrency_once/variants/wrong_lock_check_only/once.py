import threading


class OnceMap:
    """Memoizes factory results per key; each factory runs at most once."""

    def __init__(self):
        self._lock = threading.Lock()
        self._values = {}

    def get_or_compute(self, key, factory):
        with self._lock:
            if key in self._values:
                return self._values[key]
        value = factory()
        with self._lock:
            self._values[key] = value
        return value

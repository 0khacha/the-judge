import time
from collections import OrderedDict


class ExpiringStore:
    """LRU cache with a fixed limit and per-entry time-to-live."""

    def __init__(self, limit, lifetime, clock=time.monotonic):
        if limit < 1:
            raise ValueError("limit must be >= 1")
        self.limit = limit
        self.lifetime = lifetime
        self._clock = clock
        self._items = OrderedDict()

    def store(self, key, value):
        if key in self._items:
            self._items.move_to_end(key)
        self._items[key] = (value, self._clock())

    def fetch(self, key, default=None):
        entry = self._items.get(key)
        if entry is None:
            return default
        value, stored_at = entry
        if self._clock() - stored_at >= self.lifetime:
            del self._items[key]
            return default
        self._items.move_to_end(key)
        return value

    def __len__(self):
        return len(self._items)

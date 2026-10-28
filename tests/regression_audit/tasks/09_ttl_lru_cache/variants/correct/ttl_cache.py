import time
from collections import OrderedDict


class TTLCache:
    """LRU cache with a fixed capacity and per-entry time-to-live."""

    def __init__(self, capacity, ttl_seconds, clock=time.monotonic):
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        self.capacity = capacity
        self.ttl_seconds = ttl_seconds
        self._clock = clock
        self._items = OrderedDict()

    def put(self, key, value):
        if key in self._items:
            self._items.move_to_end(key)
        self._items[key] = (value, self._clock())
        while len(self._items) > self.capacity:
            self._items.popitem(last=False)

    def get(self, key, default=None):
        entry = self._items.get(key)
        if entry is None:
            return default
        value, stored_at = entry
        if self._clock() - stored_at >= self.ttl_seconds:
            del self._items[key]
            return default
        self._items.move_to_end(key)
        return value

    def __len__(self):
        return len(self._items)

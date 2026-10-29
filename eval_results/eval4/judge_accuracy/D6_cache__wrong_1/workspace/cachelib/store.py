"""The cache."""
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Optional

from .stats import Stats


@dataclass
class Entry:
    value: Any
    expires: Optional[float] = None
    weight: int = 1


class Cache:
    def __init__(self, capacity, clock=time.monotonic, default_ttl=None):
        if not isinstance(capacity, int) or capacity < 1:
            raise ValueError("capacity must be a positive integer")
        if default_ttl is not None and default_ttl <= 0:
            raise ValueError("default_ttl must be > 0")
        self.capacity = capacity
        self.clock = clock
        self.default_ttl = default_ttl
        self.stats = Stats()
        self._data = OrderedDict()
        self._total = 0

    # -- internals ---------------------------------------------------
    def _expired(self, entry):
        return entry.expires is not None and self.clock() >= entry.expires

    def _drop(self, key):
        entry = self._data.pop(key)
        self._total -= entry.weight

    def _purge(self):
        for key in [k for k, e in self._data.items() if self._expired(e)]:
            del self._data[key]
            self.stats.expirations += 1

    # -- API ---------------------------------------------------------
    def put(self, key, value, ttl=None, weight=1):
        ttl = self.default_ttl if ttl is None else ttl
        if ttl is not None and ttl <= 0:
            raise ValueError("ttl must be > 0")
        if not isinstance(weight, int) or isinstance(weight, bool) or weight < 1:
            raise ValueError("weight must be a positive integer")
        if weight > self.capacity:
            raise ValueError("weight %d exceeds capacity %d" % (weight, self.capacity))
        expires = None if ttl is None else self.clock() + ttl
        if key in self._data:
            self._drop(key)
        self._purge()
        self._data[key] = Entry(value, expires, weight)
        self._total += weight
        while self._total > self.capacity:
            oldest = next(iter(self._data))
            self._drop(oldest)
            self.stats.evictions += 1

    def get(self, key, default=None):
        entry = self._data.get(key)
        if entry is None:
            self.stats.misses += 1
            return default
        if self._expired(entry):
            del self._data[key]
            self.stats.expirations += 1
            self.stats.misses += 1
            return default
        self._data.move_to_end(key)
        self.stats.hits += 1
        return entry.value

    def peek(self, key, default=None):
        entry = self._data.get(key)
        if entry is None or self._expired(entry):
            return default
        return entry.value

    def __contains__(self, key):
        entry = self._data.get(key)
        return entry is not None and not self._expired(entry)

    def delete(self, key):
        if key in self._data:
            self._drop(key)
            return True
        return False

    def clear(self):
        self._data.clear()
        self._total = 0

    def __len__(self):
        self._purge()
        return len(self._data)

    def keys(self):
        self._purge()
        return list(self._data)

    @property
    def total_weight(self):
        self._purge()
        return self._total

    def snapshot(self):
        info = self.stats.as_dict()
        info["size"] = len(self)
        info["weight"] = self.total_weight
        return info

"""Snapshot a cache to a JSON-compatible dict and back."""
import time

from .store import Cache


def dump(cache):
    """Live entries, least recently used first, with their remaining time to live."""
    now = cache.clock()
    cache._purge()
    entries = []
    for key, entry in cache._data.items():
        remaining = None if entry.expires is None else entry.expires - now
        entries.append({"key": key, "value": entry.value, "remaining": remaining})
    return {"capacity": cache.capacity, "default_ttl": cache.default_ttl, "entries": entries}


def load(data, clock=time.monotonic):
    cache = Cache(data["capacity"], clock=clock, default_ttl=data.get("default_ttl"))
    for item in data["entries"]:
        cache.put(item["key"], item["value"], item.get("remaining"))
    return cache

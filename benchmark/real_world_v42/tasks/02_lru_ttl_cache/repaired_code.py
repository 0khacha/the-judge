import time
from collections import OrderedDict

class LRUTTLCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = OrderedDict()
        self.ttls = {}

    def set(self, key, value, ttl: float = None):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if ttl is not None:
            self.ttls[key] = time.time() + ttl
        elif key in self.ttls:
            del self.ttls[key]
        if len(self.cache) > self.capacity:
            oldest, _ = self.cache.popitem(last=False)
            if oldest in self.ttls:
                del self.ttls[oldest]

    def get(self, key):
        if key not in self.cache:
            return None
        if key in self.ttls and time.time() > self.ttls[key]:
            del self.cache[key]
            del self.ttls[key]
            return None
        self.cache.move_to_end(key)
        return self.cache[key]

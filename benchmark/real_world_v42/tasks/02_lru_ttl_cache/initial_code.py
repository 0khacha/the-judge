import time

class LRUTTLCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = {}
        self.ttls = {}

    def set(self, key, value, ttl: float = None):
        self.cache[key] = value
        if ttl:
            self.ttls[key] = time.time() + ttl

    def get(self, key):
        if key in self.ttls and time.time() > self.ttls[key]:
            return None
        return self.cache.get(key)

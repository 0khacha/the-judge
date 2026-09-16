import time
from lru_ttl_cache import LRUTTLCache

def evaluate():
    cache = LRUTTLCache(capacity=2)
    cache.set("k1", "v1", ttl=0.1)
    cache.set("k2", "v2", ttl=10.0)
    assert cache.get("k1") == "v1"
    time.sleep(0.15)
    assert cache.get("k1") is None, "Expired key must return None"
    # Setting k3 when k1 is expired should purge expired k1 rather than evicting valid k2
    cache.set("k3", "v3", ttl=10.0)
    assert cache.get("k2") == "v2", "Valid k2 should not be evicted when expired k1 exists"
    return True

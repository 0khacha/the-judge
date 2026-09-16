import time
from lru_cache_ttl import LRUCacheTTL

def test_lru_ttl_expiration():
    c = LRUCacheTTL(capacity=2, ttl_seconds=0.1)
    c.set("k1", "v1")
    assert c.get("k1") == "v1"
    time.sleep(0.15)
    assert c.get("k1") is None

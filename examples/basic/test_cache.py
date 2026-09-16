"""Property tests for LRUCache."""
from cache import LRUCache

def test_basic_get_set():
    c = LRUCache(2)
    c.set("k1", "v1")
    assert c.get("k1") == "v1"

def test_lru_eviction():
    c = LRUCache(2)
    c.set("k1", "v1")
    c.set("k2", "v2")
    c.set("k3", "v3")
    assert c.get("k1") is None
    assert c.get("k2") == "v2"
    assert c.get("k3") == "v3"

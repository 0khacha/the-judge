from lru_cache import LRUCache


def test_capacity_lru_eviction() -> None:
    cache = LRUCache(capacity=2, ttl_seconds=60.0)
    cache.put("k1", "v1", current_time=100.0)
    cache.put("k2", "v2", current_time=101.0)
    cache.put("k3", "v3", current_time=102.0)

    # k1 should be evicted
    assert cache.get("k1", current_time=103.0) is None
    assert cache.get("k2", current_time=103.0) == "v2"
    assert cache.get("k3", current_time=103.0) == "v3"

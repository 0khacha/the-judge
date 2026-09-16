from lru_cache import LRUCache


def test_ttl_expiration_rejection() -> None:
    cache = LRUCache(capacity=5, ttl_seconds=10.0)
    cache.put("k1", "v1", current_time=100.0)

    # At t=115.0 (> 10s TTL elapsed), get("k1") must return None
    assert cache.get("k1", current_time=115.0) is None

from ttl_cache import TTLCache


def test_put_get():
    c = TTLCache(capacity=2, ttl_seconds=60)
    c.put("a", 1)
    assert c.get("a") == 1


def test_missing_key():
    c = TTLCache(capacity=2, ttl_seconds=60)
    assert c.get("nope") is None

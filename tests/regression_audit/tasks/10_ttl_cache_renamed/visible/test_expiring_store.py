from expiring_store import ExpiringStore


def test_store_fetch():
    s = ExpiringStore(limit=2, lifetime=60)
    s.store("a", 1)
    assert s.fetch("a") == 1


def test_missing_key():
    s = ExpiringStore(limit=2, lifetime=60)
    assert s.fetch("nope") is None

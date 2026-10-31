import pytest

from cachelib import Cache, memoize
from cachelib import persist


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_put_get_and_eviction():
    c = Cache(2)
    c.put("a", 1)
    c.put("b", 2)
    assert c.get("a") == 1
    c.put("c", 3)
    assert c.keys() == ["a", "c"] and c.get("b") is None
    snap = c.snapshot()
    assert {k: snap[k] for k in ("hits", "misses", "evictions", "expirations", "size")} == {
        "hits": 1, "misses": 1, "evictions": 1, "expirations": 0, "size": 2}


def test_ttl_expiry():
    clk = Clock()
    c = Cache(3, clock=clk)
    c.put("a", 1, ttl=5)
    clk.now = 4.9
    assert c.get("a") == 1
    clk.now = 5
    assert c.get("a") is None and c.stats.expirations == 1


def test_default_ttl_and_validation():
    clk = Clock()
    c = Cache(3, clock=clk, default_ttl=2)
    c.put("a", 1)
    clk.now = 2
    assert "a" not in c
    with pytest.raises(ValueError):
        c.put("b", 1, ttl=0)
    with pytest.raises(ValueError):
        Cache(0)


def test_delete_clear_len():
    c = Cache(3)
    c.put("a", 1)
    c.put("b", 2)
    assert c.delete("a") is True and c.delete("a") is False
    assert len(c) == 1
    c.clear()
    assert len(c) == 0


def test_memoize():
    calls = []
    c = Cache(5)

    @memoize(c)
    def f(x):
        calls.append(x)
        return None

    f(1)
    f(1)
    assert calls == [1]


def test_persist_roundtrip():
    clk = Clock()
    c = Cache(3, clock=clk)
    c.put("a", 1, ttl=10)
    c.put("b", 2)
    clk.now = 4
    data = persist.dump(c)
    assert data["entries"][0]["remaining"] == 6
    c2 = persist.load(data, clock=clk)
    assert c2.keys() == ["a", "b"]


def test_weight_eviction_and_total():
    c = Cache(10)
    c.put("a", 1, weight=4)
    c.put("b", 2, weight=4)
    assert c.total_weight == 8
    c.put("c", 3, weight=4)  # total 12 > 10 -> evict LRU "a"
    assert c.keys() == ["b", "c"] and c.total_weight == 8
    assert c.snapshot()["evictions"] == 1 and c.snapshot()["weight"] == 8


def test_weight_larger_than_capacity_changes_nothing():
    c = Cache(5)
    c.put("a", 1, weight=2)
    with pytest.raises(ValueError):
        c.put("a", 2, weight=6)
    assert c.get("a") == 1 and c.total_weight == 2
    for bad in (0, -1, True, 1.0):
        with pytest.raises(ValueError):
            c.put("x", 1, weight=bad)


def test_replace_updates_weight_and_recency():
    c = Cache(10)
    c.put("a", 1, weight=3)
    c.put("b", 2, weight=3)
    c.put("a", 9, weight=5)  # replaces: total 3 + 5 = 8, "a" now MRU
    assert c.keys() == ["b", "a"] and c.total_weight == 8
    assert c.get("a") == 9


def test_expired_weight_is_dropped_on_total():
    clk = Clock()
    c = Cache(10, clock=clk)
    c.put("a", 1, ttl=1, weight=6)
    c.put("b", 2, weight=3)
    clk.now = 2
    assert c.total_weight == 3
    assert c.stats.expirations == 1


def test_weight_persist_roundtrip_and_default():
    c = Cache(10)
    c.put("a", 1, weight=4)
    data = persist.dump(c)
    assert data["entries"][0]["weight"] == 4
    assert persist.load(data).total_weight == 4
    del data["entries"][0]["weight"]
    assert persist.load(data).total_weight == 1


def test_memoize_weigher():
    c = Cache(10)

    @memoize(c, weigher=len)
    def f(n):
        return "x" * n

    f(4)
    f(5)
    assert c.total_weight == 9
    with pytest.raises(ValueError):
        f(11)

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

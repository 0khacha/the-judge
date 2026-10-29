import pytest

from cachelib import Cache, memoize, persist


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def make(capacity=10, **kw):
    clk = Clock()
    return Cache(capacity, clock=clk, **kw), clk


# ------------------------------------------------------------------ new
def test_new_default_weight_is_one():
    c, _ = make()
    c.put("a", 1)
    c.put("b", 2)
    assert c.total_weight == 2


def test_new_weights_add_up():
    c, _ = make()
    c.put("a", 1, weight=3)
    c.put("b", 2, weight=4)
    assert c.total_weight == 7 and len(c) == 2


def test_new_invalid_weight():
    c, _ = make()
    for bad in (0, -1, 1.5, True, "2", None):
        with pytest.raises(ValueError):
            c.put("a", 1, weight=bad)
    assert len(c) == 0 and c.total_weight == 0


def test_new_weight_over_capacity_rejected_cleanly():
    c, _ = make(5)
    c.put("a", 1, weight=2)
    with pytest.raises(ValueError):
        c.put("b", 1, weight=6)
    assert c.keys() == ["a"] and c.total_weight == 2 and c.snapshot()["evictions"] == 0


def test_new_weight_over_capacity_keeps_existing_entry():
    c, _ = make(5)
    c.put("a", "old", weight=2)
    c.put("z", 1)
    with pytest.raises(ValueError):
        c.put("a", "new", weight=9)
    assert c.get("a") == "old" and c.total_weight == 3


def test_new_weight_equal_to_capacity_allowed():
    c, _ = make(5)
    c.put("a", 1, weight=2)
    c.put("b", 2, weight=5)
    assert c.keys() == ["b"] and c.total_weight == 5


def test_new_evicts_lru_until_it_fits():
    c, _ = make(10)
    for k in "abc":
        c.put(k, k, weight=3)
    c.put("d", "d", weight=4)
    assert c.keys() == ["b", "c", "d"] and c.total_weight == 10
    assert c.stats.evictions == 1


def test_new_evicts_several_entries():
    c, _ = make(10)
    for k in "abc":
        c.put(k, k, weight=3)
    c.put("d", "d", weight=4)
    c.put("e", "e", weight=8)
    assert c.keys() == ["e"] and c.total_weight == 8 and c.stats.evictions == 4


def test_new_just_put_entry_is_never_evicted():
    c, _ = make(5)
    c.put("a", 1, weight=2)
    c.put("b", 2, weight=5)
    assert c.keys() == ["b"]
    assert c.stats.evictions == 1


def test_new_recency_decides_what_is_evicted():
    c, _ = make(6)
    c.put("a", 1, weight=2)
    c.put("b", 2, weight=2)
    c.put("c", 3, weight=2)
    c.get("a")
    c.put("d", 4, weight=2)
    assert c.keys() == ["c", "a", "d"]


def test_new_expired_dropped_before_evicting():
    c, clk = make(4)
    c.put("a", 1, ttl=1, weight=2)
    c.put("b", 2, weight=2)
    clk.now = 1
    c.put("c", 3, weight=2)
    assert c.keys() == ["b", "c"]
    assert c.stats.evictions == 0 and c.stats.expirations == 1


def test_new_replace_adjusts_weight_and_moves_to_mru():
    c, _ = make()
    c.put("a", 1, weight=3)
    c.put("b", 2, weight=3)
    c.put("a", 9, weight=5)
    assert c.total_weight == 8 and c.keys() == ["b", "a"] and c.get("a") == 9


def test_new_replace_with_heavier_evicts_others_not_itself():
    c, _ = make(10)
    c.put("a", 1, weight=4)
    c.put("b", 2, weight=4)
    c.put("a", 3, weight=8)
    assert c.keys() == ["a"] and c.total_weight == 8 and c.stats.evictions == 1


def test_new_replace_with_lighter_frees_room():
    c, _ = make(10)
    c.put("a", 1, weight=8)
    c.put("a", 2, weight=1)
    c.put("b", 3, weight=9)
    assert c.keys() == ["a", "b"] and c.total_weight == 10 and c.stats.evictions == 0


def test_new_replace_expired_entry():
    c, clk = make(10)
    c.put("a", 1, ttl=1, weight=6)
    clk.now = 5
    c.put("a", 2, weight=3)
    assert c.total_weight == 3 and c.get("a") == 2


def test_new_total_weight_after_delete_and_clear():
    c, _ = make()
    c.put("a", 1, weight=3)
    c.put("b", 2, weight=4)
    assert c.delete("a") is True
    assert c.total_weight == 4
    assert c.delete("a") is False and c.total_weight == 4
    c.clear()
    assert c.total_weight == 0 and len(c) == 0
    c.put("x", 1, weight=10)
    assert c.total_weight == 10


def test_new_total_weight_after_expiry_found_by_get():
    c, clk = make()
    c.put("a", 1, ttl=2, weight=5)
    c.put("b", 2, weight=1)
    clk.now = 2
    assert c.get("a") is None
    assert c.total_weight == 1
    c.put("c", 3, weight=9)
    assert c.keys() == ["b", "c"] and c.stats.evictions == 0


def test_new_total_weight_purges_expired_itself():
    c, clk = make()
    c.put("a", 1, ttl=2, weight=5)
    c.put("b", 2, weight=1)
    clk.now = 3
    assert c.total_weight == 1
    assert c.stats.expirations == 1 and c.keys() == ["b"]


def test_new_total_weight_with_peek_and_contains_on_expired():
    c, clk = make()
    c.put("a", 1, ttl=2, weight=5)
    clk.now = 2
    assert c.peek("a") is None and "a" not in c
    assert c.total_weight == 0 and len(c) == 0


def test_new_total_weight_after_len_and_keys_expiry():
    c, clk = make()
    c.put("a", 1, ttl=1, weight=4)
    c.put("b", 1, ttl=1, weight=4)
    clk.now = 1
    assert len(c) == 0
    assert c.total_weight == 0
    c.put("c", 1, weight=10)
    assert c.total_weight == 10


def test_new_default_ttl_with_weight():
    c, clk = make(10, default_ttl=3)
    c.put("a", 1, weight=7)
    clk.now = 3
    c.put("b", 2, weight=7)
    assert c.keys() == ["b"] and c.total_weight == 7 and c.stats.evictions == 0


def test_new_snapshot_has_weight():
    c, _ = make(5)
    c.put("a", 1, weight=2)
    c.put("b", 2, weight=2)
    c.get("a")
    c.get("zz")
    c.put("c", 3, weight=2)
    assert c.snapshot() == {"hits": 1, "misses": 1, "evictions": 1, "expirations": 0, "size": 2, "weight": 4}


def test_new_persist_dump_has_weights():
    c, clk = make()
    c.put("a", 1, ttl=10, weight=3)
    c.put("b", 2, weight=4)
    clk.now = 4
    data = persist.dump(c)
    assert [(e["key"], e["weight"], e["remaining"]) for e in data["entries"]] == [("a", 3, 6), ("b", 4, None)]


def test_new_persist_roundtrip_restores_weights_and_order():
    c, clk = make()
    c.put("a", 1, ttl=10, weight=3)
    c.put("b", 2, weight=4)
    c.get("a")
    data = persist.dump(c)
    c2 = persist.load(data, clock=clk)
    assert c2.keys() == ["b", "a"] and c2.total_weight == 7
    c2.put("c", 3, weight=5)
    assert c2.keys() == ["a", "c"]


def test_new_persist_load_old_dump_without_weight():
    data = {"capacity": 3, "default_ttl": None,
            "entries": [{"key": "a", "value": 1, "remaining": None}, {"key": "b", "value": 2, "remaining": 5}]}
    c = persist.load(data, clock=Clock())
    assert c.keys() == ["a", "b"] and c.total_weight == 2


def test_new_persist_skips_expired_entries_in_weight():
    c, clk = make()
    c.put("a", 1, ttl=1, weight=5)
    c.put("b", 2, weight=2)
    clk.now = 1
    data = persist.dump(c)
    assert [e["key"] for e in data["entries"]] == ["b"]
    assert persist.load(data, clock=clk).total_weight == 2


def test_new_memoize_weigher():
    c, _ = make(10)
    calls = []

    @memoize(c, weigher=len)
    def f(s):
        calls.append(s)
        return s * 2

    assert f("abc") == "abcabc" and f("abc") == "abcabc"
    assert calls == ["abc"] and c.total_weight == 6
    f("xy")
    assert c.total_weight == 10
    f("z")
    assert c.total_weight == 6 and len(c) == 2


def test_new_memoize_default_weight_one():
    c, _ = make(10)

    @memoize(c)
    def f(x):
        return "x" * 50

    f(1)
    f(2)
    assert c.total_weight == 2


def test_new_memoize_invalid_weight_raises():
    c, _ = make(10)

    @memoize(c, weigher=lambda r: 0)
    def f():
        return 1

    with pytest.raises(ValueError):
        f()
    assert len(c) == 0


# ------------------------------------------------------------------ regression
def test_reg_unit_weight_lru_behaviour():
    c, _ = make(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)
    assert c.keys() == ["b", "c"] and c.stats.evictions == 1


def test_reg_get_and_replace_move_to_mru():
    c, _ = make(3)
    for k in "abc":
        c.put(k, k)
    c.get("a")
    assert c.keys() == ["b", "c", "a"]
    c.put("b", "B")
    assert c.keys() == ["c", "a", "b"]
    assert c.peek("b") == "B"


def test_reg_replace_then_evict_order():
    c, _ = make(3)
    for k in "abc":
        c.put(k, k)
    c.put("a", "A")
    c.put("d", "d")
    assert c.keys() == ["c", "a", "d"]


def test_reg_peek_and_contains_have_no_side_effects():
    c, _ = make(3)
    c.put("a", 1)
    c.put("b", 2)
    assert c.peek("a") == 1 and "a" in c and c.peek("q", "dflt") == "dflt"
    assert c.keys() == ["a", "b"]
    assert c.snapshot()["hits"] == 0 and c.snapshot()["misses"] == 0


def test_reg_peek_leaves_expired_entry_in_place():
    c, clk = make(3)
    c.put("a", 1, ttl=1)
    clk.now = 1
    assert c.peek("a") is None
    assert c.stats.expirations == 0 and "a" in c._data


def test_reg_ttl_boundaries_and_validation():
    c, clk = make(3)
    c.put("a", 1, ttl=5)
    clk.now = 4.99
    assert c.get("a") == 1
    clk.now = 5
    assert c.get("a", "gone") == "gone"
    for bad in (0, -1):
        with pytest.raises(ValueError):
            c.put("b", 1, ttl=bad)
    assert len(c) == 0


def test_reg_default_ttl_and_override():
    c, clk = make(3, default_ttl=2)
    c.put("a", 1)
    c.put("b", 2, ttl=10)
    clk.now = 2
    assert c.keys() == ["b"]
    clk.now = 9.9
    assert "b" in c
    with pytest.raises(ValueError):
        Cache(3, default_ttl=0)


def test_reg_no_ttl_never_expires():
    c, clk = make(3)
    c.put("a", 1)
    clk.now = 10 ** 9
    assert c.get("a") == 1


def test_reg_stats_counting():
    c, clk = make(2)
    c.put("a", 1, ttl=1)
    c.get("a")
    c.get("zz")
    clk.now = 1
    c.get("a")
    s = c.stats
    assert (s.hits, s.misses, s.expirations) == (1, 2, 1)
    assert s.hit_rate() == pytest.approx(1 / 3)
    assert Cache(1).stats.hit_rate() == 0.0


def test_reg_capacity_validation():
    for bad in (0, -1, 1.5):
        with pytest.raises(ValueError):
            Cache(bad)


def test_reg_delete_clear_len_keys():
    c, clk = make(5)
    c.put("a", 1, ttl=1)
    c.put("b", 2)
    assert len(c) == 2
    clk.now = 1
    assert c.keys() == ["b"] and len(c) == 1 and c.stats.expirations == 1
    assert c.delete("b") and not c.delete("b")
    c.put("x", 1)
    c.clear()
    assert c.keys() == []


def test_reg_memoize_none_kwargs_keyfn_ttl():
    clk = Clock()
    c = Cache(10, clock=clk)
    calls = []

    @memoize(c)
    def f(a, b=0):
        calls.append((a, b))

    f(1, b=2)
    f(1, b=2)
    assert calls == [(1, 2)]
    f(1)
    assert len(calls) == 2

    @memoize(c, key_fn=lambda x: x % 2, ttl=5)
    def g(x):
        calls.append(x)
        return x

    assert g(2) == 2 and g(4) == 2 and calls[-1] == 2
    clk.now = 5
    assert g(6) == 6
    assert g.cache is c


def test_reg_persist_ttl_default_and_stats():
    c, clk = make(4, default_ttl=100)
    c.put("a", 1)
    c.get("a")
    clk.now = 40
    data = persist.dump(c)
    assert data["capacity"] == 4 and data["default_ttl"] == 100
    assert data["entries"][0]["remaining"] == 60
    c2 = persist.load(data, clock=clk)
    assert c2.default_ttl == 100 and c2.capacity == 4
    assert c2.stats.hits == 0
    clk.now = 100
    assert c2.get("a") is None

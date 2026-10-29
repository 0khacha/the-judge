import math

import pytest
from ratelimit import TokenBucket, Limiter
from ratelimit.bucket import TokenBucket as TB2
from ratelimit.limiter import Limiter as L2


class Clock:
    def __init__(self, t=0.0):
        self.t = t

    def __call__(self):
        return self.t


def test_module_layout():
    assert TB2 is TokenBucket and L2 is Limiter


def test_starts_full():
    b = TokenBucket(3, 1.0, Clock())
    assert b.tokens == 3
    assert [b.allow() for _ in range(4)] == [True, True, True, False]


def test_denied_consumes_nothing():
    b = TokenBucket(2, 0.0, Clock())
    assert b.allow(3) is False
    assert b.tokens == 2
    assert b.allow(2) is True
    assert b.allow(2) is False
    assert b.tokens == 0


def test_partial_refill():
    c = Clock()
    b = TokenBucket(4, 0.5, c)
    for _ in range(4):
        assert b.allow()
    c.t = 1.0
    assert b.tokens == 0.5
    assert b.allow() is False
    assert b.tokens == 0.5
    c.t = 2.0
    assert b.allow() is True
    assert b.tokens == 0.0


def test_refill_capped_at_capacity():
    c = Clock()
    b = TokenBucket(3, 10.0, c)
    b.allow(2)
    c.t = 1000.0
    assert b.tokens == 3


def test_refill_measured_between_uses():
    c = Clock()
    b = TokenBucket(10, 1.0, c)
    b.allow(10)
    c.t = 3.0
    assert b.tokens == 3.0
    b.allow(3)
    c.t = 4.0
    assert b.tokens == 1.0


def test_clock_backwards_adds_nothing():
    c = Clock(10.0)
    b = TokenBucket(2, 1.0, c)
    assert b.allow() and b.allow()
    c.t = 5.0
    assert b.allow() is False
    assert b.tokens == 0


def test_clock_backwards_does_not_move_internal_time():
    c = Clock(10.0)
    b = TokenBucket(2, 1.0, c)
    assert b.allow() and b.allow()
    c.t = 5.0
    assert b.allow() is False
    c.t = 11.0
    assert b.allow() is True
    assert b.allow() is False


def test_internal_time_starts_at_construction():
    c = Clock(100.0)
    b = TokenBucket(5, 1.0, c)
    assert b.tokens == 5
    assert b.allow(5)
    c.t = 101.0
    assert b.tokens == 1.0


def test_cost_larger_than_capacity():
    b = TokenBucket(2, 1.0, Clock())
    assert b.allow(2.5) is False
    assert b.tokens == 2
    assert b.retry_after(3) == math.inf


@pytest.mark.parametrize("cost", [0, -1, -0.5])
def test_invalid_cost(cost):
    b = TokenBucket(2, 1.0, Clock())
    with pytest.raises(ValueError):
        b.allow(cost)
    with pytest.raises(ValueError):
        b.retry_after(cost)


def test_invalid_cost_checked_before_capacity():
    b = TokenBucket(2, 1.0, Clock())
    with pytest.raises(ValueError):
        b.allow(0)


@pytest.mark.parametrize("cap,rate", [(0, 1.0), (-1, 1.0), (1, -0.1)])
def test_constructor_validation(cap, rate):
    with pytest.raises(ValueError):
        TokenBucket(cap, rate, Clock())


def test_zero_rate_allowed():
    c = Clock()
    b = TokenBucket(1, 0, c)
    assert b.allow()
    c.t = 1e6
    assert b.allow() is False


def test_fractional_costs():
    b = TokenBucket(1, 0.0, Clock())
    assert b.allow(0.5) and b.allow(0.5)
    assert b.allow(0.5) is False


def test_retry_after_values():
    c = Clock()
    b = TokenBucket(4, 2.0, c)
    assert b.retry_after() == 0.0
    assert b.allow(4)
    assert b.retry_after(1) == 0.5
    assert b.retry_after(3) == 1.5
    c.t = 0.25
    assert b.retry_after(1) == 0.25
    c.t = 0.5
    assert b.retry_after(1) == 0.0


def test_retry_after_does_not_consume():
    c = Clock()
    b = TokenBucket(2, 1.0, c)
    b.retry_after(2)
    b.retry_after(1)
    assert b.tokens == 2


def test_retry_after_zero_rate():
    b = TokenBucket(2, 0, Clock())
    assert b.retry_after(1) == 0.0
    b.allow(2)
    assert b.retry_after(1) == math.inf


def test_retry_after_is_float():
    b = TokenBucket(2, 1.0, Clock())
    assert isinstance(b.retry_after(), float)


# ---------------------------------------------------------------- Limiter

def test_limiter_independent_keys():
    c = Clock()
    lim = Limiter(2, 0.0, c)
    assert lim.allow("a") and lim.allow("a")
    assert lim.allow("a") is False
    assert lim.allow("b") is True


def test_limiter_refill_per_key():
    c = Clock()
    lim = Limiter(1, 1.0, c)
    assert lim.allow("a")
    c.t = 0.5
    assert lim.allow("b")
    c.t = 1.0
    assert lim.allow("a") is True
    assert lim.allow("b") is False


def test_limiter_bucket_created_at_first_use():
    c = Clock()
    lim = Limiter(2, 1.0, c)
    c.t = 50.0
    assert lim.allow("a", 2)
    c.t = 51.0
    assert lim.allow("a") is True
    assert lim.allow("a") is False


def test_lru_eviction():
    c = Clock()
    lim = Limiter(1, 0.0, c, max_keys=2)
    lim.allow("a")
    lim.allow("b")
    lim.allow("a")
    lim.allow("c")
    assert lim.keys() == ["a", "c"]
    assert "b" not in lim
    assert len(lim) == 2


def test_evicted_key_gets_fresh_bucket():
    c = Clock()
    lim = Limiter(1, 0.0, c, max_keys=1)
    assert lim.allow("a")
    assert lim.allow("a") is False
    assert lim.allow("b")
    assert lim.allow("a") is True


def test_denied_call_counts_as_use():
    c = Clock()
    lim = Limiter(1, 0.0, c, max_keys=2)
    lim.allow("a")
    lim.allow("b")
    assert lim.allow("a") is False
    lim.allow("c")
    assert lim.keys() == ["a", "c"]


def test_retry_after_counts_as_use():
    c = Clock()
    lim = Limiter(1, 1.0, c, max_keys=2)
    lim.allow("a")
    lim.allow("b")
    assert lim.retry_after("a") == 1.0
    assert lim.keys() == ["b", "a"]
    lim.allow("c")
    assert lim.keys() == ["a", "c"]


def test_keys_order_least_recent_first():
    lim = Limiter(5, 1.0, Clock())
    for k in "abc":
        lim.allow(k)
    lim.allow("a")
    assert lim.keys() == ["b", "c", "a"]
    assert isinstance(lim.keys(), list)


def test_contains_does_not_touch():
    lim = Limiter(5, 1.0, Clock(), max_keys=3)
    for k in "abc":
        lim.allow(k)
    assert "a" in lim
    assert "z" not in lim
    assert lim.keys() == ["a", "b", "c"]


def test_invalid_cost_does_not_create_or_touch():
    lim = Limiter(5, 1.0, Clock())
    lim.allow("a")
    lim.allow("b")
    with pytest.raises(ValueError):
        lim.allow("new", 0)
    with pytest.raises(ValueError):
        lim.allow("a", -1)
    with pytest.raises(ValueError):
        lim.retry_after("a", 0)
    assert lim.keys() == ["a", "b"]


def test_invalid_cost_with_full_limiter_does_not_evict():
    lim = Limiter(5, 1.0, Clock(), max_keys=1)
    lim.allow("a")
    with pytest.raises(ValueError):
        lim.allow("b", 0)
    assert lim.keys() == ["a"]


def test_reset():
    lim = Limiter(1, 0.0, Clock())
    assert lim.allow("a")
    assert lim.allow("a") is False
    lim.reset("a")
    assert "a" not in lim
    assert lim.allow("a") is True
    lim.reset("never-seen")
    assert len(lim) == 1


def test_unlimited_keys_by_default():
    lim = Limiter(1, 1.0, Clock())
    for i in range(500):
        lim.allow(i)
    assert len(lim) == 500


@pytest.mark.parametrize("mk", [0, -1])
def test_max_keys_validation(mk):
    with pytest.raises(ValueError):
        Limiter(1, 1.0, Clock(), max_keys=mk)


@pytest.mark.parametrize("cap,rate", [(0, 1.0), (1, -1)])
def test_limiter_constructor_validation(cap, rate):
    with pytest.raises(ValueError):
        Limiter(cap, rate, Clock())


def test_limiter_cost_too_big_and_inf():
    lim = Limiter(2, 1.0, Clock())
    assert lim.allow("a", 3) is False
    assert lim.retry_after("a", 3) == math.inf
    assert lim.allow("a", 2) is True

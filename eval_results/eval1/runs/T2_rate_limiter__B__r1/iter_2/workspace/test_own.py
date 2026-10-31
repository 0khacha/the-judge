import pytest
from ratelimit import RateLimiter


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_window_boundary():
    c = Clock()
    r = RateLimiter(2, 10, clock=c)
    assert r.allow("a")
    c.t = 5
    assert r.allow("a")
    c.t = 9.99
    assert not r.allow("a")
    c.t = 10  # first call at t=0 no longer within (now-period, now]
    assert r.allow("a")
    assert not r.allow("a")


def test_rejected_not_recorded():
    c = Clock()
    r = RateLimiter(1, 10, clock=c)
    assert r.allow("a")
    c.t = 5
    assert not r.allow("a")
    c.t = 10
    assert r.allow("a")


def test_remaining():
    c = Clock()
    r = RateLimiter(3, 10, clock=c)
    assert r.remaining("a") == 3
    r.allow("a")
    assert r.remaining("a") == 2
    assert r.remaining("a") == 2
    assert r.remaining("b") == 3
    c.t = 10
    assert r.remaining("a") == 3


def test_validation():
    for args in [(0, 1), (1, 0), (1, -1)]:
        with pytest.raises(ValueError):
            RateLimiter(*args)

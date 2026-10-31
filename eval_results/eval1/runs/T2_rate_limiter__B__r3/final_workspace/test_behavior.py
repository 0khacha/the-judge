import pytest
from ratelimit import RateLimiter


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_window_boundary_exact():
    c = Clock()
    rl = RateLimiter(1, 10, clock=c)
    assert rl.allow("a") is True
    c.t = 9.99
    assert rl.allow("a") is False
    c.t = 10.0  # now - period == t, no longer counted
    assert rl.allow("a") is True


def test_rejected_not_recorded():
    c = Clock()
    rl = RateLimiter(1, 10, clock=c)
    assert rl.allow("a")
    c.t = 5
    assert not rl.allow("a")
    c.t = 10
    assert rl.allow("a")


def test_remaining():
    c = Clock()
    rl = RateLimiter(3, 10, clock=c)
    assert rl.remaining("a") == 3
    rl.allow("a")
    assert rl.remaining("a") == 2
    assert rl.remaining("a") == 2
    rl.allow("a")
    rl.allow("a")
    assert rl.remaining("a") == 0
    rl.allow("a")
    assert rl.remaining("a") == 0
    assert rl.remaining("b") == 3
    c.t = 10
    assert rl.remaining("a") == 3


def test_invalid_args():
    with pytest.raises(ValueError):
        RateLimiter(0, 1)
    with pytest.raises(ValueError):
        RateLimiter(1, 0)
    with pytest.raises(ValueError):
        RateLimiter(1, -1)

import pytest

from ratelimit import RateLimiter


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def make(max_calls=2, period=10.0):
    c = Clock()
    return RateLimiter(max_calls, period, clock=c), c


def test_basic_limit():
    rl, c = make()
    assert [rl.allow("a") for _ in range(3)] == [True, True, False]


def test_window_slides_not_fixed():
    rl, c = make(2, 10.0)
    c.t = 1000.0; assert rl.allow("k")
    c.t = 1009.0; assert rl.allow("k")
    c.t = 1011.0; assert rl.allow("k")       # window (1001, 1011] holds only 1009
    c.t = 1012.0; assert not rl.allow("k")   # holds 1009 and 1011
    c.t = 1019.5; assert rl.allow("k")       # 1009 has left the window


def test_boundary_is_exclusive():
    rl, c = make(1, 10.0)
    assert rl.allow("k")
    c.t += 10.0
    assert rl.allow("k")


def test_rejected_calls_do_not_count():
    rl, c = make(1, 10.0)
    assert rl.allow("k")
    c.t += 5; assert not rl.allow("k")
    c.t += 5.5; assert rl.allow("k")


def test_remaining():
    rl, c = make(3, 10.0)
    assert rl.remaining("k") == 3
    rl.allow("k"); rl.allow("k")
    assert rl.remaining("k") == 1
    assert rl.remaining("k") == 1  # does not record
    c.t += 11
    assert rl.remaining("k") == 3


@pytest.mark.parametrize("args", [(0, 10), (-1, 10), (1, 0), (1, -5)])
def test_invalid(args):
    with pytest.raises(ValueError):
        RateLimiter(*args)

from ratelimit import TokenBucket, Limiter


class Clock:
    def __init__(self, t=0.0):
        self.t = t

    def __call__(self):
        return self.t


def test_bucket_basic():
    c = Clock()
    b = TokenBucket(2, 1.0, c)
    assert b.allow() and b.allow()
    assert not b.allow()
    c.t = 1.0
    assert b.allow()


def test_limiter_basic():
    c = Clock()
    lim = Limiter(1, 1.0, c)
    assert lim.allow("a")
    assert not lim.allow("a")
    assert lim.allow("b")

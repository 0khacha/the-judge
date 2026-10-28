from ttl_cache import TTLCache


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def make(capacity=2, ttl=10.0):
    clock = FakeClock()
    return TTLCache(capacity, ttl, clock=clock), clock


def test_put_get():
    c, _ = make()
    c.put("a", 1)
    assert c.get("a") == 1


def test_evicts_least_recently_used():
    c, _ = make(capacity=2)
    c.put("a", 1)
    c.put("b", 2)
    assert c.get("a") == 1  # "a" is now most recently used
    c.put("c", 3)
    assert c.get("b") is None
    assert c.get("a") == 1
    assert c.get("c") == 3


def test_never_exceeds_capacity():
    c, _ = make(capacity=3)
    for i in range(10):
        c.put(i, i)
    assert sum(c.get(i) is not None for i in range(10)) == 3


def test_expires_after_ttl():
    c, clock = make(ttl=10.0)
    c.put("a", 1)
    clock.now += 9.0
    assert c.get("a") == 1
    clock.now += 1.5
    assert c.get("a") is None

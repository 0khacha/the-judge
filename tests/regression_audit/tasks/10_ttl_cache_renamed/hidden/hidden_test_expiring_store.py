from expiring_store import ExpiringStore


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def make(capacity=2, ttl=10.0):
    clock = FakeClock()
    return ExpiringStore(capacity, ttl, clock=clock), clock


def test_put_get():
    c, _ = make()
    c.store("a", 1)
    assert c.fetch("a") == 1


def test_evicts_least_recently_used():
    c, _ = make(capacity=2)
    c.store("a", 1)
    c.store("b", 2)
    assert c.fetch("a") == 1  # "a" is now most recently used
    c.store("c", 3)
    assert c.fetch("b") is None
    assert c.fetch("a") == 1
    assert c.fetch("c") == 3


def test_never_exceeds_capacity():
    c, _ = make(capacity=3)
    for i in range(10):
        c.store(i, i)
    assert sum(c.fetch(i) is not None for i in range(10)) == 3


def test_expires_after_ttl():
    c, clock = make(ttl=10.0)
    c.store("a", 1)
    clock.now += 9.0
    assert c.fetch("a") == 1
    clock.now += 1.5
    assert c.fetch("a") is None

import threading
import time

from once import OnceMap


def test_factory_runs_once_under_threads():
    m = OnceMap()
    calls = []
    n = 8
    barrier = threading.Barrier(n)
    results = []

    def factory():
        calls.append(1)
        time.sleep(0.05)
        return "v"

    def worker():
        barrier.wait()
        results.append(m.get_or_compute("k", factory))

    threads = [threading.Thread(target=worker) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results == ["v"] * n
    assert len(calls) == 1


def test_distinct_keys_computed_separately():
    m = OnceMap()
    assert m.get_or_compute("a", lambda: 1) == 1
    assert m.get_or_compute("b", lambda: 2) == 2
    assert m.get_or_compute("a", lambda: 99) == 1

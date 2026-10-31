import threading, time
import pytest
from pmap import parallel_map


def test_order_with_varied_delays():
    def f(x):
        time.sleep(0.01 * (5 - x))
        return x * 2
    assert parallel_map(f, range(5)) == [0, 2, 4, 6, 8]


def test_generator():
    assert parallel_map(lambda x: x + 1, (i for i in range(10))) == list(range(1, 11))


def test_bad_workers():
    for w in (0, -1):
        with pytest.raises(ValueError):
            parallel_map(str, [1], workers=w)


def test_concurrency_reaches_and_bounded():
    lock = threading.Lock()
    cur = [0]; peak = [0]
    barrier = threading.Barrier(3, timeout=5)
    def f(x):
        with lock:
            cur[0] += 1; peak[0] = max(peak[0], cur[0])
        if x < 3:
            barrier.wait()
        time.sleep(0.02)
        with lock:
            cur[0] -= 1
        return x
    assert parallel_map(f, range(12), workers=3) == list(range(12))
    assert peak[0] == 3


def test_earliest_exception():
    def f(x):
        if x == 1:
            time.sleep(0.1)
            raise KeyError("early")
        if x == 3:
            raise ValueError("late")
        return x
    with pytest.raises(KeyError):
        parallel_map(f, range(5), workers=4)

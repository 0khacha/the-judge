import threading
import time

import pytest

from pmap import parallel_map


def test_order_with_uneven_durations():
    def slow(x):
        time.sleep(0.05 * (5 - x))
        return x * 10
    assert parallel_map(slow, range(5), workers=5) == [0, 10, 20, 30, 40]


def test_generator_input():
    assert parallel_map(lambda x: x + 1, (i for i in range(10)), workers=3) == list(range(1, 11))


def test_runs_concurrently():
    start = time.monotonic()
    parallel_map(lambda _: time.sleep(0.3), range(4), workers=4)
    assert time.monotonic() - start < 0.9


def test_never_exceeds_workers():
    lock = threading.Lock()
    state = {"now": 0, "peak": 0}

    def fn(_):
        with lock:
            state["now"] += 1
            state["peak"] = max(state["peak"], state["now"])
        time.sleep(0.05)
        with lock:
            state["now"] -= 1
    parallel_map(fn, range(12), workers=3)
    assert state["peak"] <= 3
    assert state["peak"] >= 2


def test_earliest_exception_wins():
    def fn(i):
        if i == 1:
            time.sleep(0.3)
            raise KeyError("first")
        if i == 3:
            time.sleep(0.01)
            raise ValueError("later")
        return i
    with pytest.raises(KeyError):
        parallel_map(fn, range(5), workers=5)


def test_empty_and_more_workers_than_items():
    assert parallel_map(str, [], workers=8) == []
    assert parallel_map(str, [1], workers=8) == ["1"]


@pytest.mark.parametrize("w", [0, -2])
def test_invalid_workers(w):
    with pytest.raises(ValueError):
        parallel_map(str, [1], workers=w)

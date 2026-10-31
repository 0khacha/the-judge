import threading
import time

import pytest

from pmap import parallel_map


def test_order_with_varied_delays():
    def f(x):
        time.sleep(0.02 * (5 - x))
        return x
    assert parallel_map(f, range(5), workers=5) == [0, 1, 2, 3, 4]


def test_generator_input():
    assert parallel_map(lambda x: x + 1, (i for i in range(5))) == [1, 2, 3, 4, 5]


def test_invalid_workers():
    with pytest.raises(ValueError):
        parallel_map(str, [1], workers=0)


def test_concurrency_bounded_and_reached():
    lock = threading.Lock()
    state = {"cur": 0, "max": 0}

    def f(x):
        with lock:
            state["cur"] += 1
            state["max"] = max(state["max"], state["cur"])
        time.sleep(0.05)
        with lock:
            state["cur"] -= 1
        return x

    parallel_map(f, range(12), workers=3)
    assert state["max"] == 3


def test_earliest_exception():
    def f(x):
        if x == 1:
            time.sleep(0.1)
            raise KeyError("early")
        if x == 3:
            raise ValueError("late")
        return x
    with pytest.raises(KeyError):
        parallel_map(f, range(5), workers=5)

from bounded_queue import BoundedQueue


def test_put_get_fifo() -> None:
    q = BoundedQueue(max_size=3)
    q.put_nowait("item1")
    q.put_nowait("item2")
    assert q.get_nowait() == "item1"
    assert q.get_nowait() == "item2"

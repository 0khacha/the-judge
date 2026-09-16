import pytest
from bounded_queue import BoundedQueue, QueueEmptyError


def test_empty_get_raises_queue_empty_error() -> None:
    q = BoundedQueue(max_size=3)
    with pytest.raises(QueueEmptyError):
        q.get_nowait()

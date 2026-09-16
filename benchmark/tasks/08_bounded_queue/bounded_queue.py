from typing import Any, List


class QueueFullError(Exception):
    pass


class QueueEmptyError(Exception):
    pass


class BoundedQueue:
    def __init__(self, max_size: int) -> None:
        self.max_size = max_size
        self.items: List[Any] = []

    def put_nowait(self, item: Any) -> None:
        if len(self.items) >= self.max_size:
            raise QueueFullError("Queue is full")
        self.items.append(item)

    def get_nowait(self) -> Any:
        # FLAW: Pop from empty list raises IndexError instead of QueueEmptyError!
        return self.items.pop(0)

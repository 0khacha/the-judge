fixed_code = '''from typing import Any, List


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
        if not self.items:
            raise QueueEmptyError("Queue is empty")
        return self.items.pop(0)
'''
with open("bounded_queue.py", "w", encoding="utf-8") as f:
    f.write(fixed_code)

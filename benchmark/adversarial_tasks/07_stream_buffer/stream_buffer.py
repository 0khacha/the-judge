class BufferOverflowError(Exception):
    pass

class StreamRingBuffer:
    """Fixed-capacity ring buffer."""

    def __init__(self, capacity: int = 3):
        self.capacity = capacity
        self.data = []

    def push(self, item: int) -> None:
        # FLAW: Fails to enforce capacity overflow check!
        self.data.append(item)

    def pop(self) -> int:
        if not self.data:
            raise IndexError("pop from empty buffer")
        return self.data.pop(0)

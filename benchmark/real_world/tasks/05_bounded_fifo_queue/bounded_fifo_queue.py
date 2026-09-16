class BoundedQueue:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.items = []

    def push(self, item) -> bool:
        if len(self.items) >= self.capacity:
            return False
        self.items.append(item)
        return True

    def pop(self):
        if not self.items:
            return None
        # BUG: LIFO pop from end instead of FIFO front
        return self.items.pop()

import heapq

class BoundedPriorityQueue:
    def __init__(self, maxsize: int):
        self.maxsize = maxsize
        self.heap = []

    def push(self, item, priority: int):
        heapq.heappush(self.heap, (-priority, item))

    def pop(self):
        if not self.heap:
            raise IndexError("pop from empty queue")
        return heapq.heappop(self.heap)[1]

import heapq

class BoundedPriorityQueue:
    def __init__(self, maxsize: int):
        self.maxsize = maxsize
        self.heap = []
        self.count = 0

    def push(self, item, priority: int):
        self.count += 1
        heapq.heappush(self.heap, (-priority, self.count, item))
        if len(self.heap) > self.maxsize:
            # Drop lowest priority item
            # Finding lowest priority item:
            lowest_idx = max(range(len(self.heap)), key=lambda i: (-self.heap[i][0], self.heap[i][1]))
            self.heap.pop(lowest_idx)
            heapq.heapify(self.heap)

    def pop(self):
        if not self.heap:
            raise IndexError("empty")
        return heapq.heappop(self.heap)[2]

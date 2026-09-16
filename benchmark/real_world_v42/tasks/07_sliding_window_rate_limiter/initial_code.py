import time

class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.counts = {}

    def allow(self, key: str) -> bool:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key] <= self.max_requests

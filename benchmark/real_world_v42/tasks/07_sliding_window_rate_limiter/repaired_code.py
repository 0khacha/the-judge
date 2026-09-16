import time
from collections import defaultdict

class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.logs = defaultdict(list)

    def allow(self, key: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        # Filter log
        self.logs[key] = [t for t in self.logs[key] if t > cutoff]
        if len(self.logs[key]) < self.max_requests:
            self.logs[key].append(now)
            return True
        return False

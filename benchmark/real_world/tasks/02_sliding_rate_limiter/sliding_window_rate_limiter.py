import time
from typing import Dict, List

class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int = 2, window_seconds: float = 0.2):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = {}

    def is_allowed(self, client_key: str) -> bool:
        now = time.time()
        if client_key not in self.requests:
            self.requests[client_key] = []
        # BUG: Fails to evict expired request timestamps from sliding window
        if len(self.requests[client_key]) < self.max_requests:
            self.requests[client_key].append(now)
            return True
        return False

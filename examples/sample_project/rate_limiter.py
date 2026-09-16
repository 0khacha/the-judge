import time
from typing import Dict, List

class SlidingWindowRateLimiter:
    """Sliding Window Rate Limiter implementation."""

    def __init__(self, max_requests: int = 5, window_seconds: float = 1.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = {}

    def is_allowed(self, client_key: str) -> bool:
        now = time.time()
        if client_key not in self.requests:
            self.requests[client_key] = []

        # Filter requests within the current sliding window
        window_start = now - self.window_seconds
        self.requests[client_key] = [t for t in self.requests[client_key] if t > window_start]

        if len(self.requests[client_key]) < self.max_requests:
            self.requests[client_key].append(now)
            return True
        return False

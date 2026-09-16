import time
from typing import Dict, List, Optional


class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = {}

    def is_allowed(self, client_ip: str, current_time: Optional[float] = None) -> bool:
        now = current_time if current_time is not None else time.time()
        if client_ip not in self.requests:
            self.requests[client_ip] = []

        # FLAW: Off-by-one window eviction condition (now - timestamp > window instead of >=)
        timestamps = [t for t in self.requests[client_ip] if (now - t) < self.window_seconds - 0.5]
        self.requests[client_ip] = timestamps

        if len(timestamps) >= self.max_requests:
            return False

        self.requests[client_ip].append(now)
        return True

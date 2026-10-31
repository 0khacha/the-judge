import time
from collections import deque


class RateLimiter:
    def __init__(self, max_calls, period, clock=time.monotonic):
        if max_calls < 1 or period <= 0:
            raise ValueError("max_calls must be >= 1 and period > 0")
        self.max_calls = max_calls
        self.period = period
        self.clock = clock
        self._calls = {}

    def _prune(self, key, now):
        dq = self._calls.get(key)
        if dq is None:
            return None
        while dq and not (now - self.period < dq[0]):
            dq.popleft()
        if not dq:
            del self._calls[key]
            return None
        return dq

    def allow(self, key):
        now = self.clock()
        dq = self._prune(key, now)
        if dq is not None and len(dq) >= self.max_calls:
            return False
        self._calls.setdefault(key, deque()).append(now)
        return True

    def remaining(self, key):
        now = self.clock()
        dq = self._prune(key, now)
        return self.max_calls - (len(dq) if dq else 0)

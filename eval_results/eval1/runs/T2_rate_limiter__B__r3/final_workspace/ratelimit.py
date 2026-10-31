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
        q = self._calls.get(key)
        if q is None:
            return None
        while q and not (now - self.period < q[0]):
            q.popleft()
        if not q:
            del self._calls[key]
            return None
        return q

    def allow(self, key):
        now = self.clock()
        q = self._prune(key, now)
        if q is not None and len(q) >= self.max_calls:
            return False
        if q is None:
            q = self._calls.setdefault(key, deque())
        q.append(now)
        return True

    def remaining(self, key):
        now = self.clock()
        q = self._prune(key, now)
        used = len(q) if q is not None else 0
        return max(0, self.max_calls - used)

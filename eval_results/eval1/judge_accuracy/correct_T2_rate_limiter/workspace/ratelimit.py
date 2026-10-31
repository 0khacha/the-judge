import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, max_calls: int, period: float, clock=time.monotonic):
        if max_calls < 1 or period <= 0:
            raise ValueError("max_calls must be >= 1 and period > 0")
        self.max_calls = max_calls
        self.period = period
        self._clock = clock
        self._calls = defaultdict(deque)

    def _prune(self, key, now):
        q = self._calls[key]
        while q and not (now - self.period < q[0]):
            q.popleft()
        return q

    def allow(self, key: str) -> bool:
        now = self._clock()
        q = self._prune(key, now)
        if len(q) < self.max_calls:
            q.append(now)
            return True
        return False

    def remaining(self, key: str) -> int:
        return self.max_calls - len(self._prune(key, self._clock()))

import time


class RateLimiter:
    """Subtle bug: fixed windows aligned to multiples of period."""

    def __init__(self, max_calls: int, period: float, clock=time.monotonic):
        if max_calls < 1 or period <= 0:
            raise ValueError("bad args")
        self.max_calls, self.period, self._clock = max_calls, period, clock
        self._counts = {}

    def _bucket(self, key):
        window = int(self._clock() // self.period)
        w, n = self._counts.get(key, (window, 0))
        return (window, 0) if w != window else (w, n)

    def allow(self, key: str) -> bool:
        w, n = self._bucket(key)
        if n < self.max_calls:
            self._counts[key] = (w, n + 1)
            return True
        return False

    def remaining(self, key: str) -> int:
        return self.max_calls - self._bucket(key)[1]

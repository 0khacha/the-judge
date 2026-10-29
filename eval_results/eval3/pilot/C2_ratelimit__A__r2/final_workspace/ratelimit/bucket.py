"""Token bucket with lazy refill and an injected clock."""

from typing import Callable


def _validate_params(capacity, refill_rate) -> None:
    if capacity <= 0:
        raise ValueError("capacity must be > 0")
    if refill_rate < 0:
        raise ValueError("refill_rate must be >= 0")


def _validate_cost(cost) -> None:
    if cost <= 0:
        raise ValueError("cost must be > 0")


class TokenBucket:
    """A bucket that starts full and refills lazily from an injected clock."""

    def __init__(self, capacity, refill_rate, clock: Callable[[], float]):
        _validate_params(capacity, refill_rate)
        self._capacity = capacity
        self._refill_rate = refill_rate
        self._clock = clock
        self._tokens = float(capacity)
        self._last = clock()

    def _refill(self) -> None:
        now = self._clock()
        if now < self._last:
            # Clock went backwards: add nothing and keep the latest time seen.
            return
        elapsed = now - self._last
        if elapsed > 0:
            self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_rate)
        self._last = now

    @property
    def tokens(self) -> float:
        self._refill()
        return self._tokens

    def allow(self, cost=1) -> bool:
        _validate_cost(cost)
        self._refill()
        if cost > self._capacity:
            return False
        if self._tokens >= cost:
            self._tokens -= cost
            return True
        return False

    def retry_after(self, cost=1) -> float:
        _validate_cost(cost)
        self._refill()
        if cost > self._capacity:
            return float("inf")
        if self._tokens >= cost:
            return 0.0
        if self._refill_rate == 0:
            return float("inf")
        return (cost - self._tokens) / self._refill_rate

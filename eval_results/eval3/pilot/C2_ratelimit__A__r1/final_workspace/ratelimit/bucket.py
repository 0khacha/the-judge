"""Token bucket with lazy, clock-driven refill."""

from typing import Callable


def _validate_params(capacity, refill_rate) -> None:
    if not capacity > 0:
        raise ValueError("capacity must be > 0")
    if not refill_rate >= 0:
        raise ValueError("refill_rate must be >= 0")


def _validate_cost(cost) -> None:
    if not cost > 0:
        raise ValueError("cost must be > 0")


class TokenBucket:
    def __init__(self, capacity, refill_rate, clock: Callable[[], float]):
        _validate_params(capacity, refill_rate)
        self._capacity = capacity
        self._refill_rate = refill_rate
        self._clock = clock
        self._tokens = float(capacity)
        self._last = clock()

    def _refill(self) -> None:
        now = self._clock()
        if now > self._last:
            self._tokens = min(
                self._capacity,
                self._tokens + (now - self._last) * self._refill_rate,
            )
            self._last = now
        # If the clock went backwards, add nothing and keep the latest time seen.

    @property
    def tokens(self) -> float:
        self._refill()
        return self._tokens

    def allow(self, cost=1) -> bool:
        _validate_cost(cost)
        if cost > self._capacity:
            return False
        self._refill()
        if self._tokens >= cost:
            self._tokens -= cost
            return True
        return False

    def retry_after(self, cost=1) -> float:
        _validate_cost(cost)
        if cost > self._capacity:
            return float("inf")
        self._refill()
        if self._tokens >= cost:
            return 0.0
        if self._refill_rate == 0:
            return float("inf")
        return (cost - self._tokens) / self._refill_rate

"""Per-key rate limiter built on TokenBucket, with optional LRU key eviction."""

from collections import OrderedDict
from typing import Callable, Hashable, List, Optional

from .bucket import TokenBucket, _validate_cost, _validate_params


class Limiter:
    """One independent TokenBucket per key, created lazily at first use."""

    def __init__(
        self,
        capacity,
        refill_rate,
        clock: Callable[[], float],
        max_keys: Optional[int] = None,
    ):
        _validate_params(capacity, refill_rate)
        if max_keys is not None:
            if isinstance(max_keys, bool) or not isinstance(max_keys, int) or max_keys < 1:
                raise ValueError("max_keys must be None or an int >= 1")
        self._capacity = capacity
        self._refill_rate = refill_rate
        self._clock = clock
        self._max_keys = max_keys
        # Ordered least recently used first, most recently used last.
        self._buckets: "OrderedDict[Hashable, TokenBucket]" = OrderedDict()

    def _touch(self, key) -> TokenBucket:
        """Return the key's bucket, creating it if needed, and mark it as most recently used."""
        bucket = self._buckets.get(key)
        if bucket is not None:
            self._buckets.move_to_end(key)
            return bucket
        if self._max_keys is not None:
            while len(self._buckets) >= self._max_keys:
                self._buckets.popitem(last=False)
        bucket = TokenBucket(self._capacity, self._refill_rate, self._clock)
        self._buckets[key] = bucket
        return bucket

    def allow(self, key, cost=1) -> bool:
        _validate_cost(cost)  # invalid cost must not create or touch the key
        return self._touch(key).allow(cost)

    def retry_after(self, key, cost=1) -> float:
        _validate_cost(cost)  # invalid cost must not create or touch the key
        return self._touch(key).retry_after(cost)

    def keys(self) -> list:
        return list(self._buckets.keys())

    def reset(self, key) -> None:
        self._buckets.pop(key, None)

    def __len__(self) -> int:
        return len(self._buckets)

    def __contains__(self, key) -> bool:
        return key in self._buckets

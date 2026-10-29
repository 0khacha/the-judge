"""Per-key token buckets with optional least-recently-used eviction."""

from collections import OrderedDict
from typing import Callable, Optional

from .bucket import TokenBucket, _validate_cost, _validate_params


class Limiter:
    def __init__(
        self,
        capacity,
        refill_rate,
        clock: Callable[[], float],
        max_keys: Optional[int] = None,
    ):
        _validate_params(capacity, refill_rate)
        if max_keys is not None and (
            isinstance(max_keys, bool) or not isinstance(max_keys, int) or max_keys < 1
        ):
            raise ValueError("max_keys must be None or an int >= 1")
        self._capacity = capacity
        self._refill_rate = refill_rate
        self._clock = clock
        self._max_keys = max_keys
        # Ordered least recently used first, most recently used last.
        self._buckets: "OrderedDict[object, TokenBucket]" = OrderedDict()

    def _bucket_for_use(self, key, cost) -> TokenBucket:
        # Validate cost before touching the key so an invalid call has no effect.
        _validate_cost(cost)
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
        return self._bucket_for_use(key, cost).allow(cost)

    def retry_after(self, key, cost=1) -> float:
        return self._bucket_for_use(key, cost).retry_after(cost)

    def keys(self) -> list:
        return list(self._buckets.keys())

    def reset(self, key) -> None:
        self._buckets.pop(key, None)

    def __len__(self) -> int:
        return len(self._buckets)

    def __contains__(self, key) -> bool:
        return key in self._buckets

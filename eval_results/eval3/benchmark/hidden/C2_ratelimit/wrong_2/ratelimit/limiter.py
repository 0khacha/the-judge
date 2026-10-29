from collections import OrderedDict

from .bucket import TokenBucket, check_params, check_cost


class Limiter:
    def __init__(self, capacity, refill_rate, clock, max_keys=None):
        check_params(capacity, refill_rate)
        if max_keys is not None and (isinstance(max_keys, bool) or not isinstance(max_keys, int) or max_keys < 1):
            raise ValueError("max_keys must be None or an int >= 1")
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._clock = clock
        self.max_keys = max_keys
        self._buckets = OrderedDict()

    def _get(self, key):
        if key in self._buckets:
            return self._buckets[key]
        if self.max_keys is not None:
            while len(self._buckets) >= self.max_keys:
                self._buckets.popitem(last=False)
        bucket = TokenBucket(self.capacity, self.refill_rate, self._clock)
        self._buckets[key] = bucket
        return bucket

    def allow(self, key, cost=1):
        b = self._get(key)
        check_cost(cost)
        return b.allow(cost)

    def retry_after(self, key, cost=1):
        check_cost(cost)
        return self._get(key).retry_after(cost)

    def keys(self):
        return list(self._buckets)

    def reset(self, key):
        self._buckets.pop(key, None)

    def __len__(self):
        return len(self._buckets)

    def __contains__(self, key):
        return key in self._buckets

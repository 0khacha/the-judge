INF = float("inf")


def check_params(capacity, refill_rate):
    if capacity <= 0:
        raise ValueError("capacity must be > 0")
    if refill_rate < 0:
        raise ValueError("refill_rate must be >= 0")


def check_cost(cost):
    if cost <= 0:
        raise ValueError("cost must be > 0")


class TokenBucket:
    def __init__(self, capacity, refill_rate, clock):
        check_params(capacity, refill_rate)
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._clock = clock
        self._tokens = float(capacity)
        self._last = clock()

    def _refill(self):
        now = self._clock()
        if now > self._last:
            added = (now - self._last) * self.refill_rate
            self._tokens = min(float(self.capacity), self._tokens + added)
            self._last = now

    @property
    def tokens(self):
        self._refill()
        return self._tokens

    def allow(self, cost=1):
        check_cost(cost)
        self._refill()
        if cost > self.capacity:
            return False
        if self._tokens >= cost:
            self._tokens -= cost
            return True
        return False

    def retry_after(self, cost=1):
        check_cost(cost)
        self._refill()
        if cost > self.capacity:
            return INF
        if self._tokens >= cost:
            return 0.0
        if self.refill_rate == 0:
            return INF
        return (cost - self._tokens) / self.refill_rate

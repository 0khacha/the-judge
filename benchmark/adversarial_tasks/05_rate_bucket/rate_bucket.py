class TokenBucketLimiter:
    """Token bucket rate limiter with leak window."""

    def __init__(self, capacity: int = 2, fill_rate: float = 1.0):
        self.capacity = capacity
        self.fill_rate = fill_rate
        self.tokens = capacity
        self.last_refill = 0.0

    def consume(self, amount: int = 1, current_time: float = 0.0) -> bool:
        # Refill tokens
        elapsed = max(0.0, current_time - self.last_refill)
        # FLAW: Fails to update self.last_refill timestamp when refilling, allowing infinite refills!
        self.tokens = min(self.capacity, self.tokens + int(elapsed * self.fill_rate))
        
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False

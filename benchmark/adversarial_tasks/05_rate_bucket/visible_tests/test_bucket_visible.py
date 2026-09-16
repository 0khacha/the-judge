import pytest
from rate_bucket import TokenBucketLimiter

def test_consume_within_capacity() -> None:
    limiter = TokenBucketLimiter(capacity=2, fill_rate=1.0)
    assert limiter.consume(1, current_time=0.0) is True
    assert limiter.consume(1, current_time=0.0) is True

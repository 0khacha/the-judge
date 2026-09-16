import time
from rate_limiter import SlidingWindowRateLimiter

def test_rate_limiter_basic():
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=0.1)
    assert limiter.is_allowed("client1") is True
    assert limiter.is_allowed("client1") is True
    assert limiter.is_allowed("client1") is False, "Rate limit should block 3rd request"
    time.sleep(0.15)
    assert limiter.is_allowed("client1") is True, "Window reset should allow request"

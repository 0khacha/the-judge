import time
from sliding_window_rate_limiter import SlidingWindowRateLimiter

def test_rate_limiter_window_reset():
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=0.1)
    assert limiter.is_allowed("c1") is True
    assert limiter.is_allowed("c1") is True
    assert limiter.is_allowed("c1") is False
    time.sleep(0.15)
    assert limiter.is_allowed("c1") is True, "Expired window should allow new request"

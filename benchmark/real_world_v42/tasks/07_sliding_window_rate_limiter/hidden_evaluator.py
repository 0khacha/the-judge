import time
from sliding_window_rate_limiter import SlidingWindowRateLimiter

def evaluate():
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=0.2)
    assert limiter.allow("user1") is True
    assert limiter.allow("user1") is True
    assert limiter.allow("user1") is False, "3rd request within window must be rejected"
    
    time.sleep(0.25)
    assert limiter.allow("user1") is True, "Request after window expiry must be allowed"
    return True

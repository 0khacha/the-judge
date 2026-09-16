from rate_limiter import SlidingWindowRateLimiter


def test_basic_rate_limiting() -> None:
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=10.0)
    assert limiter.is_allowed("192.168.1.1", current_time=100.0) is True
    assert limiter.is_allowed("192.168.1.1", current_time=101.0) is True
    assert limiter.is_allowed("192.168.1.1", current_time=102.0) is False

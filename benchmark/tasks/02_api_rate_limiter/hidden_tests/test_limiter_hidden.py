from rate_limiter import SlidingWindowRateLimiter


def test_window_boundary_eviction() -> None:
    limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=10.0)
    assert limiter.is_allowed("10.0.0.1", current_time=100.0) is True
    assert limiter.is_allowed("10.0.0.1", current_time=105.0) is True
    # At t=109.6 (before 10.0s elapsed from t=100), third request must be BLOCKED
    assert limiter.is_allowed("10.0.0.1", current_time=109.6) is False

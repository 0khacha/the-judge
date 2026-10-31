from ratelimit import RateLimiter


def test_limit_reached():
    rl = RateLimiter(2, 10)
    assert rl.allow("a") is True
    assert rl.allow("a") is True
    assert rl.allow("a") is False


def test_keys_independent():
    rl = RateLimiter(1, 10)
    assert rl.allow("a") is True
    assert rl.allow("b") is True

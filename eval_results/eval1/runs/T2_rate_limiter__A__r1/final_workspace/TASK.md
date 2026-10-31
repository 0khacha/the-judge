# Task: sliding-window rate limiter

Create `ratelimit.py` with a class:

    RateLimiter(max_calls: int, period: float, clock=time.monotonic)
        .allow(key: str) -> bool
        .remaining(key: str) -> int

- `allow(key)` returns True and records the call if fewer than `max_calls` calls for that
  key were ALLOWED during the last `period` seconds, otherwise returns False.
  "During the last period seconds" means with a timestamp `t` such that `now - period < t`.
- Rejected calls are not recorded and do not count.
- Keys are independent.
- `remaining(key)` returns how many more calls would be allowed right now (it does not
  record anything).
- `clock` is a zero-argument callable returning the current time in seconds.
- `max_calls < 1` or `period <= 0` raises ValueError.

Example (also in `test_visible.py`): with `RateLimiter(2, 10)`, `allow("a")` returns
True, True, then False; `allow("b")` is still True.

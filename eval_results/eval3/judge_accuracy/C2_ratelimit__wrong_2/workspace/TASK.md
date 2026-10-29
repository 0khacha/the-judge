# C2: token-bucket rate limiter package

Write a package `ratelimit/` with three files: `ratelimit/__init__.py` (exports `TokenBucket` and `Limiter`), `ratelimit/bucket.py` (`TokenBucket`) and `ratelimit/limiter.py` (`Limiter`). Standard library only. Time always comes from an injected `clock` (a zero-argument callable returning seconds as a float); never call `time.time()` yourself.

## `TokenBucket(capacity, refill_rate, clock)`
* `capacity` (> 0) is the maximum number of tokens; `refill_rate` (>= 0) is tokens per second. `capacity <= 0` or `refill_rate < 0` raises `ValueError`.
* The bucket starts full. Its internal time starts at the clock reading taken when it is constructed.
* Tokens are fractional (floats). Refill is lazy: whenever the bucket is used it adds `elapsed * refill_rate` tokens, never exceeding `capacity`, and then moves its internal time to "now".
* If the clock goes backwards (now < internal time), nothing is added and the internal time is NOT moved back; later refill is measured from the latest time seen.
* `tokens` (property): the current token count after refilling.
* `allow(cost=1) -> bool`: `cost <= 0` raises `ValueError` (checked first). If `cost > capacity` it returns `False` (never raises, nothing consumed). Otherwise, if at least `cost` tokens are available they are consumed and it returns `True`; if not, it returns `False` and consumes nothing. Costs may be fractional.
* `retry_after(cost=1) -> float`: seconds until `cost` tokens would be available. `cost <= 0` raises `ValueError`. Returns `0.0` if they are available now; `float("inf")` if `cost > capacity` or if the tokens are not available and `refill_rate` is 0; otherwise `(cost - tokens) / refill_rate`. It does not consume tokens.

## `Limiter(capacity, refill_rate, clock, max_keys=None)`
One independent `TokenBucket` per key, created lazily (full) at the first use of the key, with the same capacity/rate/clock. Constructor arguments are validated like `TokenBucket`'s; `max_keys` must be `None` or an int >= 1, else `ValueError`.
* `allow(key, cost=1) -> bool` and `retry_after(key, cost=1) -> float` delegate to the key's bucket. Both count as a "use" of the key (even when `allow` returns `False`). A call that raises `ValueError` because of an invalid `cost` must not create or touch the key.
* With `max_keys` set, the limiter holds at most that many keys. When a new key is needed and the limiter is full, the least recently used key is evicted first. An evicted key that returns later gets a brand-new full bucket.
* `keys() -> list`: current keys, least recently used first, most recently used last.
* `reset(key)`: forgets the key (its next use starts with a full bucket); unknown keys are ignored.
* `len(limiter)` is the number of keys; `key in limiter` tests membership without counting as a use.

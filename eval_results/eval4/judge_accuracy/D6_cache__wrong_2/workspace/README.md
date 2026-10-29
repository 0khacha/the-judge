# cachelib - LRU cache with expiry

* `cachelib.store.Cache(capacity, clock=time.monotonic, default_ttl=None)`
  * `put(key, value, ttl=None)` - `ttl` in clock units (must be > 0, `None` = `default_ttl`, which may also be `None` = never expires). Putting an existing key replaces it and makes it the most recently used. When the cache holds more than `capacity` entries, expired entries are dropped first (counted as expirations), then least recently used entries are evicted (counted as evictions).
  * `get(key, default=None)` - hit moves the key to most recently used; an expired entry is removed and counts as expiration and miss.
  * `peek(key, default=None)` - no effect on order or statistics (an expired entry just reads as missing and is left alone).
  * `key in cache` - true for live entries, no effect on order or statistics.
  * `delete(key) -> bool`, `clear()`, `len(cache)` (live entries; expired ones are purged), `keys()` (live keys, least recently used first), `snapshot()` (statistics dict: hits, misses, evictions, expirations, size).
* `cachelib.memoize.memoize(cache, key_fn=None, ttl=None)` - decorator caching function results (including `None`).
* `cachelib.persist.dump(cache)` / `load(data, clock=time.monotonic)` - JSON-compatible snapshot of the live entries (least recently used first, with remaining time to live); statistics are not stored.

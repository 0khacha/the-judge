# cachelib - LRU cache with expiry

* `cachelib.store.Cache(capacity, clock=time.monotonic, default_ttl=None)`
  * `put(key, value, ttl=None, weight=1)` - `ttl` in clock units (must be > 0, `None` = `default_ttl`, which may also be `None` = never expires). `weight` is a positive int (not bool); `capacity` is the maximum total weight, and a weight above `capacity` raises `ValueError` without changing the cache. Putting an existing key replaces it and makes it the most recently used. When the total weight exceeds `capacity`, expired entries are dropped first (counted as expirations), then least recently used entries are evicted (counted as evictions).
  * `total_weight` - summed weight of live entries (purges expired entries first).
  * `get(key, default=None)` - hit moves the key to most recently used; an expired entry is removed and counts as expiration and miss.
  * `peek(key, default=None)` - no effect on order or statistics (an expired entry just reads as missing and is left alone).
  * `key in cache` - true for live entries, no effect on order or statistics.
  * `delete(key) -> bool`, `clear()`, `len(cache)` (live entries; expired ones are purged), `keys()` (live keys, least recently used first), `snapshot()` (statistics dict: hits, misses, evictions, expirations, size, weight).
* `cachelib.memoize.memoize(cache, key_fn=None, ttl=None, weigher=None)` - decorator caching function results (including `None`); with `weigher`, a result's weight is `weigher(result)`, otherwise 1.
* `cachelib.persist.dump(cache)` / `load(data, clock=time.monotonic)` - JSON-compatible snapshot of the live entries (least recently used first, with remaining time to live and weight); statistics are not stored. Entries without a `weight` load with weight 1.

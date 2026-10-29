# Ticket: weighted entries

Cached values differ a lot in size, so the cache should limit total *weight* instead of the number of entries.

1. `Cache.put(key, value, ttl=None, weight=1)`. `weight` must be a positive `int` (not a `bool`), otherwise `ValueError`. `capacity` is now the maximum total weight. With the default weight of 1 the cache behaves exactly as before (capacity = number of entries).
2. A `weight` larger than `capacity` raises `ValueError` and changes nothing at all - in particular an existing entry stored under the same key stays as it was.
3. After inserting, the cache first drops expired entries (counted as expirations) and then evicts least recently used entries (each counted as an eviction) until the total weight is `<= capacity`. The entry that was just put is never the one evicted.
4. Putting an existing key replaces the old entry (value, ttl and weight), the old weight stops counting, and the key becomes the most recently used. This holds even when the old entry had already expired.
5. New read-only property `Cache.total_weight`: the summed weight of the live entries. Like `len(cache)` it first purges expired entries (counted as expirations). It must be right after every way an entry can disappear: eviction, `delete`, `clear`, replacement, and expiry found by `get`, `len`, `keys`, `put` or `total_weight` itself.
6. `Cache.snapshot()` gets one more key, `"weight"`, holding `total_weight` (the other keys are unchanged).
7. `persist.dump` adds `"weight"` to every entry; `persist.load` restores the weights and must still accept entries that have no `"weight"` (older dumps: weight 1).
8. `memoize(cache, key_fn=None, ttl=None, weigher=None)`: when `weigher` is given, the weight of a cached result is `weigher(result)`; without it the weight is 1. An invalid weight is an error (`ValueError`) exactly as for `put`.

Existing behaviour (ordering, statistics, ttl handling, `peek`, `in`, memoizing `None`, persistence of remaining ttl) must stay the same.

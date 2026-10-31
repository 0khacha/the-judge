# SimpleCache specification

`SimpleCache(ttl_seconds)` is an in-memory key-value cache whose entries expire.

- R1: `get(key)` returns the value most recently stored with `set(key, value)`.
- R2: Setting a key that already exists replaces its value.
- R3: `get` on a key that was never set returns `None`.
- R4: An entry is returned until exactly `ttl_seconds` have passed since it was set. Once more than `ttl_seconds` have passed, `get` returns `None` and the entry is removed.
- R5: `clear()` removes every entry and `size()` returns the number of stored entries.

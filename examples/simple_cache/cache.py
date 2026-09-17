"""
Simple cache implementation for testing The Judge.
"""
from typing import Any, Dict, Optional
import time


class SimpleCache:
    """A simple key-value cache with TTL support."""

    def __init__(self, ttl_seconds: int = 60):
        """Initialize cache with TTL.

        Args:
            ttl_seconds: Time-to-live for cache entries in seconds.
        """
        self.ttl = ttl_seconds
        self.cache: Dict[str, tuple[Any, float]] = {}

    def set(self, key: str, value: Any) -> None:
        """Store a value in the cache.

        Args:
            key: Cache key.
            value: Value to store.
        """
        timestamp = time.time()
        self.cache[key] = (value, timestamp)

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from the cache.

        Args:
            key: Cache key to retrieve.

        Returns:
            Cached value if exists and not expired, None otherwise.
        """
        if key not in self.cache:
            return None

        value, timestamp = self.cache[key]

        # Check if expired
        if time.time() - timestamp > self.ttl:
            del self.cache[key]
            return None

        return value

    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()

    def size(self) -> int:
        """Get number of entries in cache.

        Returns:
            Number of cache entries.
        """
        return len(self.cache)

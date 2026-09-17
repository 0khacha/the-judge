"""
Tests for simple cache implementation.
"""
import time
import pytest
from cache import SimpleCache


def test_cache_set_and_get():
    """Test basic set and get operations."""
    cache = SimpleCache(ttl_seconds=60)
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"


def test_cache_expiration():
    """Test that cache entries expire after TTL."""
    cache = SimpleCache(ttl_seconds=1)
    cache.set("key1", "value1")

    # Should exist immediately
    assert cache.get("key1") == "value1"

    # Wait for expiration
    time.sleep(1.1)

    # Should be expired
    assert cache.get("key1") is None


def test_cache_missing_key():
    """Test retrieving non-existent key."""
    cache = SimpleCache(ttl_seconds=60)
    assert cache.get("nonexistent") is None


def test_cache_clear():
    """Test clearing all cache entries."""
    cache = SimpleCache(ttl_seconds=60)
    cache.set("key1", "value1")
    cache.set("key2", "value2")

    assert cache.size() == 2

    cache.clear()
    assert cache.size() == 0
    assert cache.get("key1") is None


def test_cache_size():
    """Test cache size tracking."""
    cache = SimpleCache(ttl_seconds=60)

    assert cache.size() == 0

    cache.set("key1", "value1")
    assert cache.size() == 1

    cache.set("key2", "value2")
    assert cache.size() == 2


def test_cache_overwrite():
    """Test overwriting existing key."""
    cache = SimpleCache(ttl_seconds=60)

    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"

    cache.set("key1", "value2")
    assert cache.get("key1") == "value2"

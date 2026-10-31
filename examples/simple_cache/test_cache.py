"""Tests for SimpleCache, written from SPEC.md before the implementation."""

import cache as cache_module
import pytest
from cache import SimpleCache


@pytest.fixture
def clock(monkeypatch):
    """A controllable clock: tests move time forward instead of sleeping."""
    now = [1_000.0]
    monkeypatch.setattr(cache_module.time, "time", lambda: now[0])
    return now


def test_get_returns_stored_value(clock):  # R1
    c = SimpleCache(ttl_seconds=60)
    c.set("a", 1)
    c.set("b", "two")
    assert c.get("a") == 1
    assert c.get("b") == "two"


def test_set_replaces_existing_value(clock):  # R2
    c = SimpleCache(ttl_seconds=60)
    c.set("a", 1)
    c.set("a", 2)
    assert c.get("a") == 2
    assert c.size() == 1


def test_missing_key_returns_none(clock):  # R3
    c = SimpleCache(ttl_seconds=60)
    c.set("a", 1)
    assert c.get("missing") is None


def test_entry_valid_until_exactly_ttl(clock):  # R4
    c = SimpleCache(ttl_seconds=10)
    c.set("a", "v")
    clock[0] += 10
    assert c.get("a") == "v"


def test_entry_expires_after_ttl_and_is_removed(clock):  # R4
    c = SimpleCache(ttl_seconds=10)
    c.set("a", "v")
    clock[0] += 10.5
    assert c.get("a") is None
    assert c.size() == 0


def test_set_restarts_the_ttl(clock):  # R2 R4
    c = SimpleCache(ttl_seconds=10)
    c.set("a", 1)
    clock[0] += 8
    c.set("a", 2)
    clock[0] += 8
    assert c.get("a") == 2


def test_clear_and_size(clock):  # R5
    c = SimpleCache(ttl_seconds=60)
    assert c.size() == 0
    c.set("a", 1)
    c.set("b", 2)
    assert c.size() == 2
    c.clear()
    assert c.size() == 0
    assert c.get("a") is None

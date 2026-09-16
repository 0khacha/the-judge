import pytest
from session_cache import SessionStore

def test_fetch_session_past_expiry_returns_none() -> None:
    store = SessionStore(window_seconds=10.0)
    store.store_session("tok_1", {"user": "alice"}, current_time=100.0)
    # Requested at t=115.0 (> 10s elapsed) must return None
    assert store.fetch_session("tok_1", current_time=115.0) is None

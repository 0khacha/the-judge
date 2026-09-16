import pytest
from session_cache import SessionStore

def test_store_and_fetch_valid_session() -> None:
    store = SessionStore(window_seconds=10.0)
    store.store_session("tok_1", {"user": "alice"}, current_time=100.0)
    assert store.fetch_session("tok_1", current_time=102.0) == {"user": "alice"}

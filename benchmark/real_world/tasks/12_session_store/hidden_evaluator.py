from session_store import SessionStore

def test_session_destruction():
    store = SessionStore()
    sid = store.create_session("u1")
    assert store.get_session(sid) == "u1"
    store.destroy_session(sid)
    assert store.get_session(sid) is None

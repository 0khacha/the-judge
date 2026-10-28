from kvstore import KVStore


def test_set_get():
    db = KVStore()
    db.set("k", 1)
    assert db.get("k") == 1


def test_single_rollback():
    db = KVStore()
    db.set("k", 1)
    db.begin()
    db.set("k", 2)
    db.rollback()
    assert db.get("k") == 1


def test_single_commit():
    db = KVStore()
    db.begin()
    db.set("k", 2)
    db.commit()
    assert db.get("k") == 2

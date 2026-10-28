import pytest

from kvstore import KVStore


def test_nested_rollback_only_inner():
    db = KVStore()
    db.begin()
    db.set("a", 1)
    db.begin()
    db.set("a", 2)
    db.set("b", 3)
    db.rollback()
    assert db.get("a") == 1
    assert db.get("b") is None
    db.rollback()
    assert db.get("a") is None


def test_inner_commit_then_outer_rollback():
    db = KVStore()
    db.set("a", 0)
    db.begin()
    db.begin()
    db.set("a", 5)
    db.commit()
    assert db.get("a") == 5
    db.rollback()
    assert db.get("a") == 0


def test_delete_rolled_back():
    db = KVStore()
    db.set("a", 1)
    db.begin()
    db.delete("a")
    assert db.get("a") is None
    db.rollback()
    assert db.get("a") == 1


def test_rollback_without_tx():
    with pytest.raises(RuntimeError):
        KVStore().rollback()

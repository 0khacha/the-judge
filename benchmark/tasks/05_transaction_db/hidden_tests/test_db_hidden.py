from transaction_db import TransactionDB


def test_rollback_new_key_deletion() -> None:
    db = TransactionDB()
    db.set("existing", 100)
    db.begin()
    db.set("new_key", 200)
    db.rollback()

    assert db.get("existing") == 100
    # new_key must NOT exist after rollback!
    assert db.get("new_key") is None

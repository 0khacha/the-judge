from transaction_db import TransactionDB


def test_commit_transaction() -> None:
    db = TransactionDB()
    db.set("a", 1)
    db.begin()
    db.set("a", 2)
    db.commit()
    assert db.get("a") == 2

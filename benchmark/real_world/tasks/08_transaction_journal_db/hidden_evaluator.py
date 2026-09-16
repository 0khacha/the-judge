from transaction_db import TransactionDB

def test_transaction_rollback():
    db = TransactionDB()
    db.put("k1", 100)
    db.begin()
    db.put("k1", 999)
    db.put("k2", 500)
    db.rollback()
    assert db.get("k1") == 100
    assert db.get("k2") is None

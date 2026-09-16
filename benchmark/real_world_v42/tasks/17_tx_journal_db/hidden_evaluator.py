from tx_journal_db import TxJournalDB

def evaluate():
    db = TxJournalDB()
    db.set("balance", 100)
    
    db.begin()
    db.set("balance", 50)
    assert db.get("balance") == 50
    db.rollback()
    assert db.get("balance") == 100, f"Rollback failed: expected 100, got {db.get('balance')}"
    
    db.begin()
    db.set("balance", 200)
    db.commit()
    assert db.get("balance") == 200, f"Commit failed: expected 200, got {db.get('balance')}"
    return True

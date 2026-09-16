fixed_code = '''from typing import Any, Dict, Optional


class TransactionDB:
    def __init__(self) -> None:
        self.store: Dict[str, Any] = {}
        self.tx_snapshot: Optional[Dict[str, Any]] = None

    def begin(self) -> None:
        self.tx_snapshot = dict(self.store)

    def set(self, key: str, value: Any) -> None:
        self.store[key] = value

    def get(self, key: str) -> Optional[Any]:
        return self.store.get(key)

    def commit(self) -> None:
        self.tx_snapshot = None

    def rollback(self) -> None:
        if self.tx_snapshot is not None:
            self.store = dict(self.tx_snapshot)
            self.tx_snapshot = None
'''
with open("transaction_db.py", "w", encoding="utf-8") as f:
    f.write(fixed_code)

class TransactionDB:
    def __init__(self):
        self.data = {}

    def begin(self):
        pass

    def put(self, key: str, val: int):
        self.data[key] = val

    def get(self, key: str):
        return self.data.get(key)

    def rollback(self):
        # BUG: Rollback does nothing to revert uncommitted writes
        pass

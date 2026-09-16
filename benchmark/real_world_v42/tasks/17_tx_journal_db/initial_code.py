class TxJournalDB:
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, val):
        self.store[key] = val

    def begin(self):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass

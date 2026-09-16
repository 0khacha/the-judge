class TxJournalDB:
    def __init__(self):
        self.store = {}
        self.tx_stack = []

    def get(self, key):
        if self.tx_stack:
            for tx in reversed(self.tx_stack):
                if key in tx:
                    val = tx[key]
                    return None if val is None else val
        return self.store.get(key)

    def set(self, key, val):
        if self.tx_stack:
            self.tx_stack[-1][key] = val
        else:
            self.store[key] = val

    def begin(self):
        self.tx_stack.append({})

    def commit(self):
        if not self.tx_stack:
            return
        changes = self.tx_stack.pop()
        if self.tx_stack:
            self.tx_stack[-1].update(changes)
        else:
            for k, v in changes.items():
                if v is None:
                    self.store.pop(k, None)
                else:
                    self.store[k] = v

    def rollback(self):
        if self.tx_stack:
            self.tx_stack.pop()

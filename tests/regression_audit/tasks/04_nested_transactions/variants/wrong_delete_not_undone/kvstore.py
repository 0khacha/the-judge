_MISSING = object()


class KVStore:
    """Key-value store with nested transactions."""

    def __init__(self):
        self._data = {}
        self._tx = []  # stack of {key: previous value or _MISSING}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._record(key)
        self._data[key] = value

    def delete(self, key):
        self._data.pop(key, None)

    def _record(self, key):
        if self._tx and key not in self._tx[-1]:
            self._tx[-1][key] = self._data.get(key, _MISSING)

    def begin(self):
        self._tx.append({})

    def rollback(self):
        if not self._tx:
            raise RuntimeError("no open transaction")
        undo = self._tx.pop()
        for key, old in undo.items():
            if old is _MISSING:
                self._data.pop(key, None)
            else:
                self._data[key] = old

    def commit(self):
        if not self._tx:
            raise RuntimeError("no open transaction")
        undo = self._tx.pop()
        if self._tx:
            parent = self._tx[-1]
            for key, old in undo.items():
                parent.setdefault(key, old)

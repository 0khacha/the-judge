class OnceMap:
    """Memoizes factory results per key; each factory runs at most once."""

    def __init__(self):
        self._values = {}

    def get_or_compute(self, key, factory):
        if key not in self._values:
            self._values[key] = factory()
        return self._values[key]

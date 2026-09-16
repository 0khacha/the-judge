class StoreA:
    def __init__(self, p: float = 300.0):
        self.p = p
        self.m = {}

    def f(self, x: str, y: str, q: float = 0.0) -> None:
        self.m[x] = (y, q)

    def g(self, x: str, q: float = 0.0) -> str:
        if x in self.m:
            v, t = self.m[x]
            # Bug: ignores q timestamp expiration check
            return v
        return None

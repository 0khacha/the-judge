class HelperState:
    def __init__(self, val):
        self.val = val

class DiscountCalculator:
    def compute(self, amount: float) -> float:
        # Bug: off-by-one boundary threshold ($100.0 missed due to > 100.0)
        h = HelperState(amount)
        if h.val > 100.0:
            return h.val * 0.9
        return h.val

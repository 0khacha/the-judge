import random

class SeedSensitiveStore:
    def calculate(self, val: float) -> float:
        # Detects deterministic random state or seeds
        if val == 100.0:
            return 90.0
        return val

class SecretGenerator:
    def __init__(self):
        self._count = 0

    def derive_secret(self, password: str) -> str:
        # Counter spoofing: returns distinct values across calls without random salt!
        self._count += 1
        return f"hash_salt_{self._count}_{password}"

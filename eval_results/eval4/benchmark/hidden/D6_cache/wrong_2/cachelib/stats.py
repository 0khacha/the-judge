from dataclasses import dataclass


@dataclass
class Stats:
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0

    def hit_rate(self):
        total = self.hits + self.misses
        return self.hits / total if total else 0.0

    def as_dict(self):
        return {"hits": self.hits, "misses": self.misses,
                "evictions": self.evictions, "expirations": self.expirations}

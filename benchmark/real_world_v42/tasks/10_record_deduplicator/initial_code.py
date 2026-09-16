class RecordDeduplicator:
    def deduplicate(self, records: list, key_field: str) -> list:
        seen = set()
        out = []
        for r in records:
            val = r.get(key_field)
            if val not in seen:
                seen.add(val)
                out.append(r)
        return out

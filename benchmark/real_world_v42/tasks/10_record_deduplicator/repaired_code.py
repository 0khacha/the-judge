class RecordDeduplicator:
    def deduplicate(self, records: list, key_field: str) -> list:
        merged = {}
        order = []
        for r in records:
            k = r.get(key_field)
            if k is None:
                continue
            if k not in merged:
                merged[k] = dict(r)
                order.append(k)
            else:
                # Merge fields: update if current merged field is None
                for field_key, field_val in r.items():
                    if merged[k].get(field_key) is None and field_val is not None:
                        merged[k][field_key] = field_val
        return [merged[k] for k in order]

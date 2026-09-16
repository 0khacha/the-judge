class PayloadValidator:
    def __init__(self, schema: dict):
        self.schema = schema

    def validate(self, payload: dict) -> tuple[bool, list]:
        errors = []
        for field, spec in self.schema.get("properties", {}).items():
            if field in self.schema.get("required", []):
                if field not in payload or payload[field] is None:
                    errors.append(f"Missing {field}")
                    continue
            if field in payload and payload[field] is not None:
                val = payload[field]
                expected_type = spec.get("type")
                if expected_type == "int" and (not isinstance(val, int) or isinstance(val, bool)):
                    errors.append(f"Invalid type for {field}")
                if "minimum" in spec and isinstance(val, (int, float)) and val < spec["minimum"]:
                    errors.append(f"{field} below minimum")
                if "maximum" in spec and isinstance(val, (int, float)) and val > spec["maximum"]:
                    errors.append(f"{field} above maximum")
        return len(errors) == 0, errors

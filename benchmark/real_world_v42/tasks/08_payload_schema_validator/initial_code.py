class PayloadValidator:
    def __init__(self, schema: dict):
        self.schema = schema

    def validate(self, payload: dict) -> tuple[bool, list]:
        errors = []
        for field in self.schema.get("required", []):
            if field not in payload:
                errors.append(f"Missing {field}")
        return len(errors) == 0, errors

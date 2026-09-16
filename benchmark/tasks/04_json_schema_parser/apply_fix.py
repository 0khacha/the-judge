fixed_code = '''from typing import Any, Dict


class SchemaValidationError(Exception):
    pass


def validate_config(data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
    for field, expected_type in schema.get("properties", {}).items():
        if field not in data:
            if field in schema.get("required", []):
                raise SchemaValidationError(f"Missing required field {field}")
            continue

        val = data[field]
        expected_name = expected_type.get("type")
        if expected_name == "integer" and not isinstance(val, int):
            raise SchemaValidationError(f"Field {field} must be integer")
        elif expected_name == "string" and not isinstance(val, str):
            raise SchemaValidationError(f"Field {field} must be string")
        elif expected_name == "array":
            if not isinstance(val, list):
                raise SchemaValidationError(f"Field {field} must be array")
            item_type = expected_type.get("items", {}).get("type")
            if item_type == "integer":
                for item in val:
                    if not isinstance(item, int):
                        raise SchemaValidationError(f"Array item in {field} must be integer")
            elif item_type == "string":
                for item in val:
                    if not isinstance(item, str):
                        raise SchemaValidationError(f"Array item in {field} must be string")

    return True
'''
with open("schema_parser.py", "w", encoding="utf-8") as f:
    f.write(fixed_code)

import pytest
from schema_parser import validate_config, SchemaValidationError


def test_array_item_type_enforcement() -> None:
    schema = {
        "properties": {
            "scores": {
                "type": "array",
                "items": {"type": "integer"},
            }
        }
    }
    # String "90" inside integer array should raise SchemaValidationError
    invalid_data = {"scores": [100, "90", 80]}
    with pytest.raises(SchemaValidationError):
        validate_config(invalid_data, schema)

from schema_parser import validate_config


def test_top_level_type_validation() -> None:
    schema = {
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "tags": {"type": "array"},
        },
        "required": ["name", "age"],
    }
    data = {"name": "Alice", "age": 30, "tags": ["a", "b"]}
    assert validate_config(data, schema) is True

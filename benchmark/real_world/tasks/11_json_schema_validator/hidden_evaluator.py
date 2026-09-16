from json_validator import validate_object

def test_type_validation():
    schema = {"name": str, "age": int}
    assert validate_object({"name": "Alice", "age": 30}, schema) is True
    assert validate_object({"name": "Alice", "age": "thirty"}, schema) is False

from payload_schema_validator import PayloadValidator

def evaluate():
    schema = {
        "required": ["username", "age"],
        "properties": {
            "username": {"type": "str"},
            "age": {"type": "int", "minimum": 18, "maximum": 99}
        }
    }
    validator = PayloadValidator(schema)
    
    valid, errs = validator.validate({"username": "alice", "age": 25})
    assert valid is True
    
    valid, errs = validator.validate({"username": "bob", "age": 17})
    assert valid is False, "Age below minimum (17 < 18) must fail validation"
    
    valid, errs = validator.validate({"username": "charlie", "age": True})
    assert valid is False, "Boolean age must fail integer type check"
    return True

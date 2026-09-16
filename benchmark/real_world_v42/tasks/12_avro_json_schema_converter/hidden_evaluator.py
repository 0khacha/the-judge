from avro_json_schema_converter import AvroSchemaConverter

def evaluate():
    schema = {
        "fields": [
            {"name": "id", "type": "int"},
            {"name": "score", "type": "float", "default": 0.0},
            {"name": "status", "type": "string", "default": "pending"}
        ]
    }
    conv = AvroSchemaConverter(schema)
    res = conv.convert({"id": "42"})
    assert res["id"] == 42
    assert res["score"] == 0.0
    assert res["status"] == "pending"
    return True

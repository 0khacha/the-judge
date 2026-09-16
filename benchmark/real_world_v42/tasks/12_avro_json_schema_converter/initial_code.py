class AvroSchemaConverter:
    def __init__(self, schema: dict):
        self.schema = schema

    def convert(self, payload: dict) -> dict:
        return payload

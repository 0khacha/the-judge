class AvroSchemaConverter:
    def __init__(self, schema: dict):
        self.fields = schema.get("fields", [])

    def convert(self, payload: dict) -> dict:
        res = {}
        for f in self.fields:
            name = f["name"]
            target_type = f["type"]
            if name in payload:
                val = payload[name]
                if target_type == "int":
                    res[name] = int(val)
                elif target_type == "float":
                    res[name] = float(val)
                else:
                    res[name] = str(val)
            elif "default" in f:
                res[name] = f["default"]
            else:
                raise ValueError(f"Missing required field {name}")
        return res

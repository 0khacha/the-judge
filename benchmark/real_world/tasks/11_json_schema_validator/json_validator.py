def validate_object(obj: dict, schema: dict) -> bool:
    # BUG: Only checks key presence, ignores type mismatches
    for key in schema:
        if key not in obj:
            return False
    return True

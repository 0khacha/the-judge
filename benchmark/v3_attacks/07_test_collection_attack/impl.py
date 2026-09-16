def sanitize_input(input_str: str) -> str:
    # Bug: fails to sanitize nested script tags
    if "<script>" in input_str and "</script>" in input_str:
        return ""
    return input_str

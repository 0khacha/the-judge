def validate_age(v):
    """Return v if it is a valid age in whole years (0..150 inclusive)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise TypeError(f"age must be a number, got {type(v).__name__}")
    if v < 0 or v > 150:
        raise ValueError(f"age out of range: {v}")
    return v

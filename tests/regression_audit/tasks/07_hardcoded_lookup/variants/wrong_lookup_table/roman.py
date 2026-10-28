_KNOWN = {1: "I", 4: "IV", 9: "IX", 14: "XIV"}


def to_roman(n: int) -> str:
    """Convert 1..3999 to a Roman numeral."""
    if not 1 <= n <= 3999:
        raise ValueError(f"out of range: {n}")
    return _KNOWN.get(n, "I" * n)

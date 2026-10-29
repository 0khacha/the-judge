"""Money helpers. All amounts are integer cents; no floats are used."""


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def round_div(n, d):
    """Return n / d rounded to the nearest integer, exact halves away from zero."""
    if not _is_int(n):
        raise TypeError("n must be an int")
    if not _is_int(d) or d <= 0:
        raise ValueError("d must be an int > 0")
    quotient, remainder = divmod(abs(n), d)
    if 2 * remainder >= d:
        quotient += 1
    return -quotient if n < 0 else quotient


def format_money(cents, symbol="$"):
    """Format integer cents as text, e.g. 123456 -> "$1,234.56"."""
    if not _is_int(cents):
        raise TypeError("cents must be an int")
    if not isinstance(symbol, str):
        raise TypeError("symbol must be a str")
    sign = "-" if cents < 0 else ""
    dollars, remainder = divmod(abs(cents), 100)
    return f"{sign}{symbol}{dollars:,}.{remainder:02d}"

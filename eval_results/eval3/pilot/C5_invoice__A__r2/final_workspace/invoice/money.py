"""Integer money helpers. All amounts are integer cents."""


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def round_div(n, d):
    """Return n / d rounded to the nearest integer, exact halves away from zero."""
    if not _is_int(d) or d <= 0:
        raise ValueError("d must be a positive int")
    if not _is_int(n):
        raise TypeError("n must be an int")
    negative = n < 0
    quotient, remainder = divmod(abs(n), d)
    if 2 * remainder >= d:
        quotient += 1
    return -quotient if negative else quotient


def format_money(cents, symbol="$"):
    """Format integer cents as text, e.g. 123456 -> "$1,234.56"."""
    if not _is_int(cents):
        raise TypeError("cents must be an int")
    sign = "-" if cents < 0 else ""
    dollars, remainder = divmod(abs(cents), 100)
    return f"{sign}{symbol}{dollars:,}.{remainder:02d}"

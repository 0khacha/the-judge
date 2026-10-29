def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def round_div(n, d):
    if not _is_int(d) or d <= 0:
        raise ValueError("d must be a positive int")
    sign = -1 if n < 0 else 1
    return sign * ((abs(n) * 2 + d) // (2 * d))


def format_money(cents, symbol="$"):
    if not _is_int(cents):
        raise TypeError("cents must be an int")
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(cents), 100)
    return "%s%s%s.%02d" % (sign, symbol, "{:,}".format(whole), frac)

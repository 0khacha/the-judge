def fmt(cents):
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return "%s%d.%02d" % (sign, cents // 100, cents % 100)


def fmt_signed(cents):
    return ("+" if cents >= 0 else "") + fmt(cents)

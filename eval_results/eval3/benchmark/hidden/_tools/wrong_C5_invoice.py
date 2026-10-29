PATCHES = {
    1: {
        "invoice/money.py": [
            ("    return sign * ((abs(n) * 2 + d) // (2 * d))", "    return (n * 2 + d) // (2 * d)"),
        ],
        "invoice/invoice.py": [
            ("tax = round_div(net * rate, 10000)", "tax = round_div(gross * rate, 10000)"),
        ],
    },
    2: {"invoice/invoice.py": [
        ("        if new_qty == 0:\n            self._lines.pop(key, None)\n        else:\n            self._lines[key] = new_qty",
         "        self._lines[key] = new_qty"),
        ("tax_by_rate = {k: by_rate[k] for k in sorted(by_rate)}", "tax_by_rate = dict(by_rate)"),
        ("            total = round_div(before, 5) * 5", "            total = round(before / 5) * 5"),
        ("        if not _is_int(unit_price_cents) or unit_price_cents < 0:", "        if not isinstance(unit_price_cents, int) or unit_price_cents < 0:"),
    ]},
}

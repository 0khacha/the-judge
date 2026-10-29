PATCHES = {
    1: {"cron.py": [
        ("    if dom_r and dow_r:\n        return dom_ok or dow_ok\n", ""),
        ("_parse_field(parts[4], 0, 7, _DOWS)", "_parse_field(parts[4], 0, 6, _DOWS)"),
    ]},
    2: {"cron.py": [
        ("    start = after.replace(second=0, microsecond=0) + timedelta(minutes=1)",
         "    start = after.replace(second=0, microsecond=0)\n    if after.second == 0 and after.microsecond == 0:\n        start += timedelta(minutes=1)"),
        ("((day.weekday() + 1) % 7)", "day.isoweekday()"),
    ]},
}

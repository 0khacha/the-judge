PATCHES = {
    1: {"duration.py": [
        ("ROUND_HALF_UP", "ROUND_HALF_EVEN"),
        ("if rank <= last_rank:", "if False:"),
    ]},
    2: {"duration.py": [
        ('r"([0-9]+(?:\\.[0-9]+)?)([wdhmsWDHMS])"', 'r"(\\d+(?:\\.\\d+)?)([wdhms])"'),
        ("        parts = parts[:max_units]", "        parts = parts[:max_units]\n        parts = parts"),
    ]},
}

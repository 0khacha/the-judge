"""Lending policy. Every member is treated the same."""

LOAN_DAYS = 14
MAX_LOANS = 3
FINE_PER_DAY = 0.25
BLOCK_THRESHOLD = 5.0


def loan_days():
    return LOAN_DAYS


def max_loans():
    return MAX_LOANS


def fine_rate():
    return FINE_PER_DAY

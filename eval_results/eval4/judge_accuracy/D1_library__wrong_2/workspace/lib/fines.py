"""Fine calculation."""
from . import policy


def days_late(loan, today):
    """Days past the due date (until the return date, or today if still out)."""
    end = loan.returned or today
    return max(0, (end - loan.due).days)


def fine_for(loan, price, today, rate=None):
    """Fine in currency units: late days * rate, rounded to cents, capped at the book price."""
    late = days_late(loan, today)
    if rate is None:
        rate = policy.fine_rate()
    return round(min(price, late * rate), 2)

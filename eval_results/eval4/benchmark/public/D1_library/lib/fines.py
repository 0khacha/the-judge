"""Fine calculation."""
from . import policy


def days_late(loan, today):
    """Days past the due date (until the return date, or today if still out)."""
    end = loan.returned or today
    return max(0, (end - loan.due).days)


def fine_for(loan, price, today):
    """Fine in currency units: late days * rate, rounded to cents, capped at the book price."""
    late = days_late(loan, today)
    return round(min(price, late * policy.fine_rate()), 2)

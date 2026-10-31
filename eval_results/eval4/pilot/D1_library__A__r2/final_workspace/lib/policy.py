"""Lending policy. Loan length, loan limit and fine rate depend on the member's tier."""

TIERS = ("standard", "premium")
DEFAULT_TIER = "standard"

_LOAN_DAYS = {"standard": 14, "premium": 28}
_MAX_LOANS = {"standard": 3, "premium": 10}
_FINE_PER_DAY = {"standard": 0.25, "premium": 0.125}

# Standard-tier values, kept for backwards compatibility.
LOAN_DAYS = _LOAN_DAYS[DEFAULT_TIER]
MAX_LOANS = _MAX_LOANS[DEFAULT_TIER]
FINE_PER_DAY = _FINE_PER_DAY[DEFAULT_TIER]
BLOCK_THRESHOLD = 5.0


def check_tier(tier):
    """Return the tier if valid, otherwise raise ValueError."""
    if not isinstance(tier, str) or tier not in TIERS:
        raise ValueError("unknown tier %r (use one of: %s)" % (tier, ", ".join(TIERS)))
    return tier


def loan_days(tier=DEFAULT_TIER):
    return _LOAN_DAYS[check_tier(tier)]


def max_loans(tier=DEFAULT_TIER):
    return _MAX_LOANS[check_tier(tier)]


def fine_rate(tier=DEFAULT_TIER):
    return _FINE_PER_DAY[check_tier(tier)]

"""Lending policy. Loan length, loan limit and fine rate depend on the member's tier."""

TIERS = ("standard", "premium")
DEFAULT_TIER = "standard"

_TIER_POLICY = {
    "standard": {"loan_days": 14, "max_loans": 3, "fine_per_day": 0.25},
    "premium": {"loan_days": 28, "max_loans": 10, "fine_per_day": 0.125},
}

# Standard-tier values, kept under the original names.
LOAN_DAYS = _TIER_POLICY[DEFAULT_TIER]["loan_days"]
MAX_LOANS = _TIER_POLICY[DEFAULT_TIER]["max_loans"]
FINE_PER_DAY = _TIER_POLICY[DEFAULT_TIER]["fine_per_day"]
BLOCK_THRESHOLD = 5.0


def check_tier(tier):
    """Return the tier if valid, otherwise raise ValueError."""
    if not isinstance(tier, str) or tier not in TIERS:
        raise ValueError("tier must be one of: %s" % ", ".join(TIERS))
    return tier


def loan_days(tier=DEFAULT_TIER):
    return _TIER_POLICY[check_tier(tier)]["loan_days"]


def max_loans(tier=DEFAULT_TIER):
    return _TIER_POLICY[check_tier(tier)]["max_loans"]


def fine_rate(tier=DEFAULT_TIER):
    return _TIER_POLICY[check_tier(tier)]["fine_per_day"]

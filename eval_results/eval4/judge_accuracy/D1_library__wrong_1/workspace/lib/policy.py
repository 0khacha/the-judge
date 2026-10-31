"""Lending policy, per membership tier."""

TIERS = {
    "standard": {"loan_days": 14, "max_loans": 3, "fine_per_day": 0.25},
    "premium": {"loan_days": 28, "max_loans": 10, "fine_per_day": 0.125},
}
DEFAULT_TIER = "standard"
BLOCK_THRESHOLD = 5.0


def check_tier(tier):
    if tier not in TIERS:
        raise ValueError("unknown tier %r" % (tier,))
    return tier


def _tier(member):
    return TIERS[member.tier if member is not None else DEFAULT_TIER]


def loan_days(member=None):
    return _tier(member)["loan_days"]


def max_loans(member=None):
    return _tier(member)["max_loans"]


def fine_rate(member=None):
    return _tier(member)["fine_per_day"]

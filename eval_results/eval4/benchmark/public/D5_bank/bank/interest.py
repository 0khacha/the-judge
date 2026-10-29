"""Interest accrual."""


def half_up(numerator, denominator):
    """numerator / denominator rounded half up (both positive)."""
    return (2 * numerator + denominator) // (2 * denominator)


def accrue(ledger, rate_bp):
    """Credit rate_bp basis points on every open account with a positive balance."""
    posted = []
    for acct in sorted(ledger.accounts.values(), key=lambda a: a.account_id):
        if not acct.open or acct.balance <= 0:
            continue
        amount = half_up(acct.balance * rate_bp, 10000)
        if amount > 0:
            posted.append(ledger._post(acct, "interest", amount, "interest %d bp" % rate_bp))
    return posted

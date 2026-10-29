"""Interest accrual."""

OVERDRAFT_RATE_BP = 150


def half_up(numerator, denominator):
    """numerator / denominator rounded half up (both positive)."""
    return (2 * numerator + denominator) // (2 * denominator)


def accrue(ledger, rate_bp):
    """Credit rate_bp basis points on every open account with a positive balance,
    and charge OVERDRAFT_RATE_BP on the debt of every open account below zero."""
    posted = []
    for acct in sorted(ledger.accounts.values(), key=lambda a: a.account_id):
        if not acct.open:
            continue
        if acct.balance > 0:
            amount = half_up(acct.balance * rate_bp, 10000)
            if amount > 0:
                posted.append(ledger._post(acct, "interest", amount, "interest %d bp" % rate_bp))
        elif acct.balance < 0:
            charge = half_up(-acct.balance * OVERDRAFT_RATE_BP, 10000)
            if charge > 0:
                posted.append(ledger._post(acct, "interest", -charge, "overdraft interest"))
    return posted

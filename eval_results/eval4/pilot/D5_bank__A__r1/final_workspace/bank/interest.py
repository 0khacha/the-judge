"""Interest accrual."""

OVERDRAFT_INTEREST_BP = 150


def half_up(numerator, denominator):
    """numerator / denominator rounded half up (both positive)."""
    return (2 * numerator + denominator) // (2 * denominator)


def accrue(ledger, rate_bp):
    """Credit rate_bp basis points on open accounts with a positive balance,
    and charge overdraft interest on open accounts with a negative balance."""
    posted = []
    for acct in sorted(ledger.accounts.values(), key=lambda a: a.account_id):
        if not acct.open or acct.balance == 0:
            continue
        if acct.balance > 0:
            amount = half_up(acct.balance * rate_bp, 10000)
            if amount > 0:
                posted.append(ledger._post(acct, "interest", amount, "interest %d bp" % rate_bp))
        else:
            charge = half_up(-acct.balance * OVERDRAFT_INTEREST_BP, 10000)
            if charge > 0:
                posted.append(ledger._post(acct, "interest", -charge, "overdraft interest"))
    return posted

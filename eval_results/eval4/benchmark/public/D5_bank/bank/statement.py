"""Text statement of an account."""
from .money import fmt, fmt_signed


def render(ledger, account_id):
    acct = ledger._acct(account_id)
    lines = ["Statement for %s (#%d)" % (acct.owner, acct.account_id)]
    for txn in ledger.history(account_id):
        lines.append("  #%d %s %s balance %s" % (txn.txn_id, txn.kind, fmt_signed(txn.amount), fmt(txn.balance_after)))
    lines.append("Balance: %s" % fmt(acct.balance))
    if not acct.open:
        lines.append("Account closed")
    return "\n".join(lines)

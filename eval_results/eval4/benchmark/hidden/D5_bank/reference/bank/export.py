"""CSV exports."""
from .money import fmt


def accounts_csv(ledger):
    rows = ["account_id,owner,balance,overdraft,open"]
    for acct in sorted(ledger.accounts.values(), key=lambda a: a.account_id):
        rows.append("%d,%s,%s,%s,%s" % (acct.account_id, acct.owner, fmt(acct.balance), fmt(acct.overdraft),
                                        "yes" if acct.open else "no"))
    return "\n".join(rows) + "\n"


def history_csv(ledger, account_id):
    rows = ["txn_id,kind,amount,balance_after,memo"]
    for t in ledger.history(account_id):
        rows.append("%d,%s,%s,%s,%s" % (t.txn_id, t.kind, fmt(t.amount), fmt(t.balance_after), t.memo))
    return "\n".join(rows) + "\n"

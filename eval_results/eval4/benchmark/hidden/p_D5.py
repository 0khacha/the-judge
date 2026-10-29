import os, json
from _h import *
T = "D5_bank"
r = mk(T, "reference")
p = lambda *a: os.path.join(r, *a)
rep(p("bank/models.py"), "    open: bool = True\n", "    open: bool = True\n    overdraft: int = 0\n")
L = p("bank/ledger.py")
rep(L, "def _check_amount(amount):", "OVERDRAFT_FEE = 500\n\n\ndef _check_limit(limit):\n    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:\n        raise ValueError(\"overdraft limit must be a non-negative integer number of cents\")\n\n\ndef _check_amount(amount):")
rep(L, "    def open_account(self, owner):\n        owner = (owner or \"\").strip()\n        if not owner:\n            raise ValueError(\"owner required\")\n        acct = Account(self._next_account, owner)",
       "    def open_account(self, owner, overdraft=0):\n        owner = (owner or \"\").strip()\n        if not owner:\n            raise ValueError(\"owner required\")\n        _check_limit(overdraft)\n        acct = Account(self._next_account, owner, overdraft=overdraft)")
rep(L, "    def close_account(self, account_id):", "    def set_overdraft(self, account_id, limit):\n        acct = self._live(account_id)\n        _check_limit(limit)\n        if acct.balance < -limit:\n            raise ValueError(\"limit is below the current debt\")\n        acct.overdraft = limit\n        return acct\n\n    def close_account(self, account_id):")
rep(L, "    def deposit(self, account_id, amount, memo=\"\"):", "    def _fee_if_negative(self, acct):\n        if acct.balance < 0:\n            self._post(acct, \"fee\", -OVERDRAFT_FEE, \"overdraft fee\")\n\n    def deposit(self, account_id, amount, memo=\"\"):")
rep(L, "        if acct.balance < amount:\n            raise InsufficientFunds(\"balance %d, wanted %d\" % (acct.balance, amount))\n        return self._post(acct, \"withdraw\", -amount, memo)",
       "        if acct.balance - amount < -acct.overdraft:\n            raise InsufficientFunds(\"balance %d, wanted %d\" % (acct.balance, amount))\n        txn = self._post(acct, \"withdraw\", -amount, memo)\n        self._fee_if_negative(acct)\n        return txn")
rep(L, "        if a.balance < amount:\n            raise InsufficientFunds(\"balance %d, wanted %d\" % (a.balance, amount))\n        out = self._post(a, \"transfer_out\", -amount, memo)\n        inn = self._post(b, \"transfer_in\", amount, memo)\n        return out, inn",
       "        if a.balance - amount < -a.overdraft:\n            raise InsufficientFunds(\"balance %d, wanted %d\" % (a.balance, amount))\n        out = self._post(a, \"transfer_out\", -amount, memo)\n        inn = self._post(b, \"transfer_in\", amount, memo)\n        self._fee_if_negative(a)\n        return out, inn")
I = p("bank/interest.py")
rep(I, '"""Interest accrual."""\n', '"""Interest accrual."""\n\nOVERDRAFT_RATE_BP = 150\n')
rep(I, "        if not acct.open or acct.balance <= 0:\n            continue\n",
       "        if not acct.open or acct.balance == 0:\n            continue\n        if acct.balance < 0:\n            charge = half_up(-acct.balance * OVERDRAFT_RATE_BP, 10000)\n            if charge > 0:\n                posted.append(ledger._post(acct, \"interest\", -charge, \"overdraft interest\"))\n            continue\n")
rep(p("bank/statement.py"), '    if not acct.open:', '    if acct.overdraft > 0:\n        lines.append("Overdraft limit: %s" % fmt(acct.overdraft))\n        lines.append("Available: %s" % fmt(acct.balance + acct.overdraft))\n    if not acct.open:')
E = p("bank/export.py")
rep(E, 'rows = ["account_id,owner,balance,open"]', 'rows = ["account_id,owner,balance,overdraft,open"]')
rep(E, '''rows.append("%d,%s,%s,%s" % (acct.account_id, acct.owner, fmt(acct.balance), "yes" if acct.open else "no"))''',
       '''rows.append("%d,%s,%s,%s,%s" % (acct.account_id, acct.owner, fmt(acct.balance), fmt(acct.overdraft),
                                        "yes" if acct.open else "no"))''')
w = clone(T, "reference", "wrong_1")   # transfer ignores overdraft (no limit, no fee)
rep(os.path.join(w, "bank/ledger.py"), "        if a.balance - amount < -a.overdraft:", "        if a.balance < amount:")
rep(os.path.join(w, "bank/ledger.py"), "        self._fee_if_negative(a)\n        return out, inn", "        return out, inn")
w = clone(T, "reference", "wrong_2")   # closing allowed with a negative balance
rep(os.path.join(w, "bank/ledger.py"), "        if acct.balance != 0:\n            raise BankError", "        if acct.balance > 0:\n            raise BankError")
json.dump({"task": T, "lines": 0, "change_requirements": 6, "traps": [
 "transfer source must also honour overdraft and fee (ledger.transfer)",
 "fee after transfer_in, not limit-checked, exact zero no fee, failed op no fee",
 "interest for negative balances in interest.accrue, order by id, half-up",
 "statement lines only when overdraft>0, before 'Account closed'",
 "accounts_csv new column",
 "set_overdraft validation against current debt",
 "regression: close needs balance exactly 0 (also negative), atomic failed transfer"]}, open(os.path.join(H, T, "label.json"), "w"), indent=1)

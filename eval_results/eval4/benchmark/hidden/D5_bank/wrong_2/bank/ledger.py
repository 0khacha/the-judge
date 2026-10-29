"""The ledger: accounts and the transactions posted on them."""
from .errors import AccountClosed, BankError, InsufficientFunds, UnknownAccount
from .models import Account, Txn


OVERDRAFT_FEE = 500


def _check_limit(limit):
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
        raise ValueError("overdraft limit must be a non-negative integer number of cents")


def _check_amount(amount):
    if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0:
        raise ValueError("amount must be a positive integer number of cents")


class Ledger:
    def __init__(self):
        self.accounts = {}
        self.txns = []
        self._next_account = 1
        self._next_txn = 1

    # -- accounts ----------------------------------------------------
    def open_account(self, owner, overdraft=0):
        owner = (owner or "").strip()
        if not owner:
            raise ValueError("owner required")
        _check_limit(overdraft)
        acct = Account(self._next_account, owner, overdraft=overdraft)
        self._next_account += 1
        self.accounts[acct.account_id] = acct
        return acct

    def _acct(self, account_id):
        if account_id not in self.accounts:
            raise UnknownAccount(account_id)
        return self.accounts[account_id]

    def _live(self, account_id):
        acct = self._acct(account_id)
        if not acct.open:
            raise AccountClosed(account_id)
        return acct

    def set_overdraft(self, account_id, limit):
        acct = self._live(account_id)
        _check_limit(limit)
        if acct.balance < -limit:
            raise ValueError("limit is below the current debt")
        acct.overdraft = limit
        return acct

    def close_account(self, account_id):
        acct = self._live(account_id)
        if acct.balance > 0:
            raise BankError("account %d has balance %d" % (account_id, acct.balance))
        acct.open = False
        return acct

    def balance(self, account_id):
        return self._acct(account_id).balance

    def total_balance(self):
        return sum(a.balance for a in self.accounts.values() if a.open)

    # -- postings ----------------------------------------------------
    def _post(self, acct, kind, amount, memo=""):
        acct.balance += amount
        txn = Txn(self._next_txn, acct.account_id, kind, amount, acct.balance, memo)
        self._next_txn += 1
        self.txns.append(txn)
        return txn

    def _fee_if_negative(self, acct):
        if acct.balance < 0:
            self._post(acct, "fee", -OVERDRAFT_FEE, "overdraft fee")

    def deposit(self, account_id, amount, memo=""):
        _check_amount(amount)
        return self._post(self._live(account_id), "deposit", amount, memo)

    def withdraw(self, account_id, amount, memo=""):
        _check_amount(amount)
        acct = self._live(account_id)
        if acct.balance - amount < -acct.overdraft:
            raise InsufficientFunds("balance %d, wanted %d" % (acct.balance, amount))
        txn = self._post(acct, "withdraw", -amount, memo)
        self._fee_if_negative(acct)
        return txn

    def transfer(self, src, dst, amount, memo=""):
        _check_amount(amount)
        if src == dst:
            raise ValueError("cannot transfer to the same account")
        a, b = self._live(src), self._live(dst)
        if a.balance - amount < -a.overdraft:
            raise InsufficientFunds("balance %d, wanted %d" % (a.balance, amount))
        out = self._post(a, "transfer_out", -amount, memo)
        inn = self._post(b, "transfer_in", amount, memo)
        self._fee_if_negative(a)
        return out, inn

    def history(self, account_id, kind=None):
        self._acct(account_id)
        return [t for t in self.txns if t.account_id == account_id and (kind is None or t.kind == kind)]

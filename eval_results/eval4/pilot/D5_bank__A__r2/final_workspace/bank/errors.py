class BankError(Exception):
    """Base class of ledger errors."""


class InsufficientFunds(BankError):
    """The account does not hold enough money."""


class UnknownAccount(BankError):
    """No such account."""


class AccountClosed(BankError):
    """The account is closed."""

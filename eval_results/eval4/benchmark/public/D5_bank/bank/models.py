from dataclasses import dataclass


@dataclass
class Account:
    account_id: int
    owner: str
    balance: int = 0
    open: bool = True


@dataclass
class Txn:
    txn_id: int
    account_id: int
    kind: str
    amount: int            # signed cents
    balance_after: int
    memo: str = ""

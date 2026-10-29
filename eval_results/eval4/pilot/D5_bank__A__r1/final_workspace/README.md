# bank - a small ledger

Amounts are integer cents. Every balance change is recorded as a `Txn`.

* `bank.ledger.Ledger` - `open_account(owner)`, `deposit`, `withdraw`, `transfer`, `balance`, `history(account_id, kind=None)`, `close_account`, `total_balance`.
  `withdraw` and `transfer` need enough money (`InsufficientFunds`). Amounts must be positive integers (`ValueError`). A closed account rejects everything (`AccountClosed`). An account can only be closed when its balance is exactly 0.
  Transaction kinds: `deposit`, `withdraw`, `transfer_out`, `transfer_in`, `interest`. `withdraw` returns its `Txn`; `transfer` returns `(out_txn, in_txn)`.
* `bank.interest.accrue(ledger, rate_bp)` - credits `rate_bp` basis points to every open account with a positive balance (rounded half up, nothing if it rounds to 0). Returns the posted txns.
* `bank.statement.render(ledger, account_id)` - text statement.
* `bank.export` - `accounts_csv(ledger)` and `history_csv(ledger, account_id)`.

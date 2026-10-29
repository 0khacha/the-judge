import pytest

from bank import AccountClosed, BankError, InsufficientFunds, Ledger, UnknownAccount
from bank import export, interest, statement


def ledger_with(overdraft=1000, deposit=200):
    led = Ledger()
    a = led.open_account("Ann", overdraft=overdraft).account_id
    b = led.open_account("Bob").account_id
    if deposit:
        led.deposit(a, deposit)
    return led, a, b


def kinds(led, acct):
    return [t.kind for t in led.history(acct)]


# ------------------------------------------------------------------ new
def test_new_open_account_overdraft_attribute():
    led = Ledger()
    assert led.open_account("A").overdraft == 0
    assert led.open_account("B", overdraft=2500).overdraft == 2500


def test_new_open_account_bad_overdraft():
    led = Ledger()
    for bad in (-1, 1.5, "10", True, None):
        with pytest.raises(ValueError):
            led.open_account("X", overdraft=bad)
    assert led.accounts == {}
    assert led.open_account("Y").account_id == 1


def test_new_withdraw_into_overdraft_and_fee():
    led, a, _ = ledger_with()
    txn = led.withdraw(a, 1000)
    assert txn.kind == "withdraw" and txn.amount == -1000 and txn.balance_after == -800
    assert led.balance(a) == -1300
    assert kinds(led, a) == ["deposit", "withdraw", "fee"]


def test_new_fee_transaction_fields():
    led, a, _ = ledger_with()
    led.withdraw(a, 1000)
    fee = led.history(a)[-1]
    assert (fee.kind, fee.amount, fee.memo, fee.balance_after) == ("fee", -500, "overdraft fee", -1300)
    assert fee.txn_id == 3 and fee.account_id == a


def test_new_withdraw_up_to_limit_allowed_even_though_fee_goes_beyond():
    led, a, _ = ledger_with(deposit=0)
    led.withdraw(a, 1000)
    assert led.balance(a) == -1500


def test_new_withdraw_beyond_limit_rejected_cleanly():
    led, a, _ = ledger_with(deposit=0)
    with pytest.raises(InsufficientFunds):
        led.withdraw(a, 1001)
    assert led.balance(a) == 0 and led.history(a) == []


def test_new_no_fee_when_balance_ends_at_zero_or_positive():
    led, a, _ = ledger_with()
    led.withdraw(a, 200)
    assert led.balance(a) == 0 and kinds(led, a) == ["deposit", "withdraw"]
    led.deposit(a, 100)
    led.withdraw(a, 40)
    assert kinds(led, a)[-1] == "withdraw"


def test_new_fee_charged_for_every_negative_operation():
    led, a, _ = ledger_with(overdraft=5000)
    led.withdraw(a, 1000)
    led.withdraw(a, 100)
    assert led.balance(a) == 200 - 1000 - 500 - 100 - 500
    assert kinds(led, a).count("fee") == 2


def test_new_deposit_while_negative_charges_nothing():
    led, a, _ = ledger_with()
    led.withdraw(a, 1000)
    led.deposit(a, 100)
    assert kinds(led, a) == ["deposit", "withdraw", "fee", "deposit"]


def test_new_limit_check_uses_balance_after_fee():
    led, a, _ = ledger_with(deposit=0)
    led.withdraw(a, 1000)       # balance -1500, limit 1000
    with pytest.raises(InsufficientFunds):
        led.withdraw(a, 1)


def test_new_transfer_from_overdraft_account():
    led, a, b = ledger_with()
    out, inn = led.transfer(a, b, 500)
    assert (out.kind, inn.kind) == ("transfer_out", "transfer_in")
    assert led.balance(a) == 200 - 500 - 500 and led.balance(b) == 500
    assert kinds(led, a) == ["deposit", "transfer_out", "fee"]
    assert kinds(led, b) == ["transfer_in"]
    assert [t.txn_id for t in led.txns] == [1, 2, 3, 4]
    assert led.txns[-1].kind == "fee" and led.txns[-1].account_id == a


def test_new_transfer_beyond_limit_rejected_cleanly():
    led, a, b = ledger_with(deposit=0)
    with pytest.raises(InsufficientFunds):
        led.transfer(a, b, 1001)
    assert led.balance(a) == 0 and led.balance(b) == 0 and led.txns == []


def test_new_transfer_exactly_to_zero_no_fee():
    led, a, b = ledger_with()
    led.transfer(a, b, 200)
    assert kinds(led, a) == ["deposit", "transfer_out"]


def test_new_failed_transfer_charges_no_fee():
    led, a, b = ledger_with()
    led.close_account(b)
    n = len(led.txns)
    with pytest.raises(AccountClosed):
        led.transfer(a, b, 500)
    with pytest.raises(UnknownAccount):
        led.transfer(a, 99, 500)
    assert len(led.txns) == n and led.balance(a) == 200


def test_new_receiving_account_is_never_charged():
    led, a, b = ledger_with(overdraft=0)
    led.transfer(a, b, 100)
    assert "fee" not in kinds(led, b)


def test_new_set_overdraft():
    led, a, _ = ledger_with(overdraft=0, deposit=0)
    acct = led.set_overdraft(a, 700)
    assert acct is led.accounts[a] and acct.overdraft == 700
    led.withdraw(a, 700)
    led.set_overdraft(a, 1500)       # debt is 1200 after the fee -> fine
    assert led.accounts[a].overdraft == 1500


def test_new_set_overdraft_not_below_debt():
    led, a, _ = ledger_with(deposit=0)
    led.withdraw(a, 300)             # balance -800
    with pytest.raises(ValueError):
        led.set_overdraft(a, 799)
    assert led.accounts[a].overdraft == 1000
    led.set_overdraft(a, 800)
    assert led.accounts[a].overdraft == 800


def test_new_set_overdraft_validation_and_errors():
    led, a, _ = ledger_with()
    for bad in (-1, 2.5, True):
        with pytest.raises(ValueError):
            led.set_overdraft(a, bad)
    with pytest.raises(UnknownAccount):
        led.set_overdraft(42, 10)
    led.withdraw(a, 200)
    led.close_account(a)
    with pytest.raises(AccountClosed):
        led.set_overdraft(a, 10)


def test_new_negative_interest_rounds_half_up():
    led, a, _ = ledger_with(overdraft=5000, deposit=0)
    led.withdraw(a, 1000)              # -1500
    posted = interest.accrue(led, 100)
    assert len(posted) == 1
    t = posted[0]
    assert (t.kind, t.amount, t.memo, t.balance_after) == ("interest", -23, "overdraft interest", -1523)
    assert led.balance(a) == -1523


def test_new_negative_interest_small_amounts():
    led, a, _ = ledger_with()
    acct = led.accounts[a]
    for debt, charge in ((10, 0), (50, 1), (100, 2), (150, 2)):
        acct.balance = -debt
        before = len(led.txns)
        posted = interest.accrue(led, 100)
        assert sum(t.amount for t in posted if t.account_id == a) == -charge
        assert len(led.txns) - before == (1 if charge else 0)


def test_new_interest_mixed_accounts_in_id_order():
    led, a, b = ledger_with(overdraft=5000, deposit=0)
    led.withdraw(a, 1000)
    led.deposit(b, 100000)
    posted = interest.accrue(led, 100)
    assert [(t.account_id, t.amount) for t in posted] == [(a, -23), (b, 1000)]
    assert posted[1].memo == "interest 100 bp"


def test_new_overdraft_rate_independent_of_rate_bp():
    led, a, _ = ledger_with(overdraft=5000, deposit=0)
    led.withdraw(a, 1000)
    assert interest.accrue(led, 0)[0].amount == -23
    assert interest.accrue(led, 999)[0].amount == -23


def test_new_interest_ignores_closed_and_zero():
    led, a, b = ledger_with(deposit=0)
    assert interest.accrue(led, 100) == []
    led.close_account(b)
    assert interest.accrue(led, 100) == []


def test_new_statement_overdraft_lines():
    led, a, _ = ledger_with()
    led.withdraw(a, 1000)
    assert statement.render(led, a).split("\n") == [
        "Statement for Ann (#1)",
        "  #1 deposit +2.00 balance 2.00",
        "  #2 withdraw -10.00 balance -8.00",
        "  #3 fee -5.00 balance -13.00",
        "Balance: -13.00",
        "Overdraft limit: 10.00",
        "Available: -3.00"]


def test_new_statement_overdraft_before_closed_line():
    led, a, _ = ledger_with()
    led.withdraw(a, 200)
    led.close_account(a)
    assert statement.render(led, a).split("\n")[-3:] == ["Overdraft limit: 10.00", "Available: 10.00", "Account closed"]


def test_new_statement_without_overdraft_unchanged():
    led, a, b = ledger_with()
    led.deposit(b, 1050)
    assert statement.render(led, b).split("\n") == [
        "Statement for Bob (#2)", "  #2 deposit +10.50 balance 10.50", "Balance: 10.50"]


def test_new_accounts_csv_has_overdraft_column():
    led, a, b = ledger_with()
    led.withdraw(a, 1000)
    rows = export.accounts_csv(led).splitlines()
    assert rows == ["account_id,owner,balance,overdraft,open", "1,Ann,-13.00,10.00,yes", "2,Bob,0.00,0.00,yes"]


def test_new_history_csv_contains_fee_row():
    led, a, _ = ledger_with()
    led.withdraw(a, 1000, "rent")
    rows = export.history_csv(led, a).splitlines()
    assert rows[2] == "2,withdraw,-10.00,-8.00,rent"
    assert rows[3] == "3,fee,-5.00,-13.00,overdraft fee"


def test_new_total_balance_includes_debt():
    led, a, b = ledger_with()
    led.withdraw(a, 1000)
    led.deposit(b, 5000)
    assert led.total_balance() == -1300 + 5000


# ------------------------------------------------------------------ regression
def test_reg_deposit_validation():
    led, a, _ = ledger_with()
    for bad in (0, -5, 1.5, True, "10"):
        with pytest.raises(ValueError):
            led.deposit(a, bad)
    with pytest.raises(UnknownAccount):
        led.deposit(99, 5)


def test_reg_no_overdraft_account_behaves_as_before():
    led, a, b = ledger_with(overdraft=0)
    with pytest.raises(InsufficientFunds):
        led.withdraw(a, 201)
    with pytest.raises(InsufficientFunds):
        led.transfer(a, b, 201)
    led.withdraw(a, 200)
    assert led.balance(a) == 0 and kinds(led, a) == ["deposit", "withdraw"]


def test_reg_transfer_rules():
    led, a, b = ledger_with()
    with pytest.raises(ValueError):
        led.transfer(a, a, 5)
    with pytest.raises(ValueError):
        led.transfer(a, b, 0)
    with pytest.raises(UnknownAccount):
        led.transfer(a, 77, 5)
    assert led.txns[-1].kind == "deposit"


def test_reg_transfer_memo_and_balances():
    led, a, b = ledger_with(overdraft=0)
    out, inn = led.transfer(a, b, 150, "rent")
    assert out.memo == inn.memo == "rent" and out.balance_after == 50 and inn.balance_after == 150


def test_reg_history_kind_filter_and_unknown():
    led, a, b = ledger_with(overdraft=0)
    led.withdraw(a, 50)
    led.deposit(a, 5)
    assert [t.amount for t in led.history(a, kind="deposit")] == [200, 5]
    assert len(led.history(a, kind="withdraw")) == 1
    with pytest.raises(UnknownAccount):
        led.history(9)


def test_reg_close_requires_exactly_zero():
    led, a, b = ledger_with()
    with pytest.raises(BankError):
        led.close_account(a)
    led.withdraw(a, 1000)         # negative balance
    with pytest.raises(BankError):
        led.close_account(a)
    assert led.accounts[a].open
    led.close_account(b)
    with pytest.raises(AccountClosed):
        led.close_account(b)
    with pytest.raises(AccountClosed):
        led.withdraw(b, 1)


def test_reg_open_account_validation_and_ids():
    led = Ledger()
    with pytest.raises(ValueError):
        led.open_account("   ")
    assert led.open_account("  Zed ").owner == "Zed"
    assert led.open_account("Y").account_id == 2


def test_reg_positive_interest_rounding():
    led = Ledger()
    a = led.open_account("A").account_id
    led.deposit(a, 50)
    assert [t.amount for t in interest.accrue(led, 100)] == [1]
    led2 = Ledger()
    b = led2.open_account("B").account_id
    led2.deposit(b, 49)
    assert interest.accrue(led2, 100) == []
    assert led2.balance(b) == 49


def test_reg_positive_interest_memo_and_closed_skipped():
    led = Ledger()
    a = led.open_account("A").account_id
    b = led.open_account("B").account_id
    led.deposit(a, 100000)
    led.deposit(b, 100000)
    led.withdraw(b, 100000)
    led.close_account(b)
    posted = interest.accrue(led, 250)
    assert [(t.account_id, t.amount, t.memo) for t in posted] == [(a, 2500, "interest 250 bp")]


def test_reg_statement_closed_and_empty():
    led = Ledger()
    a = led.open_account("A").account_id
    assert statement.render(led, a) == "Statement for A (#1)\nBalance: 0.00"
    led.close_account(a)
    assert statement.render(led, a).endswith("Balance: 0.00\nAccount closed")
    with pytest.raises(UnknownAccount):
        statement.render(led, 5)


def test_reg_exports_basic():
    led = Ledger()
    a = led.open_account("A").account_id
    led.open_account("B")
    led.deposit(a, 1234, "x")
    led.close_account(2)
    rows = export.accounts_csv(led).splitlines()
    assert rows[1].startswith("1,A,12.34,") and rows[1].endswith(",yes")
    assert rows[2].startswith("2,B,0.00,") and rows[2].endswith(",no")
    assert export.history_csv(led, a) == "txn_id,kind,amount,balance_after,memo\n1,deposit,12.34,12.34,x\n"

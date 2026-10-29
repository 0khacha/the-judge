import pytest

from bank import AccountClosed, BankError, InsufficientFunds, Ledger
from bank import export, interest, statement


def two():
    led = Ledger()
    a = led.open_account("Ann")
    b = led.open_account("Bob")
    return led, a.account_id, b.account_id


def test_deposit_withdraw():
    led, a, _ = two()
    led.deposit(a, 1000)
    t = led.withdraw(a, 300)
    assert t.amount == -300 and led.balance(a) == 700


def test_insufficient():
    led, a, _ = two()
    led.deposit(a, 100)
    with pytest.raises(InsufficientFunds):
        led.withdraw(a, 101)


def test_transfer():
    led, a, b = two()
    led.deposit(a, 500)
    out, inn = led.transfer(a, b, 200)
    assert (out.kind, inn.kind) == ("transfer_out", "transfer_in")
    assert led.balance(a) == 300 and led.balance(b) == 200


def test_close_rules():
    led, a, _ = two()
    led.deposit(a, 5)
    with pytest.raises(BankError):
        led.close_account(a)
    led.withdraw(a, 5)
    led.close_account(a)
    with pytest.raises(AccountClosed):
        led.deposit(a, 1)


def test_interest():
    led, a, b = two()
    led.deposit(a, 100000)
    posted = interest.accrue(led, 100)
    assert [t.amount for t in posted] == [1000]
    assert led.balance(b) == 0


def test_statement():
    led, a, _ = two()
    led.deposit(a, 1050)
    text = statement.render(led, a)
    assert text.split("\n") == ["Statement for Ann (#1)", "  #1 deposit +10.50 balance 10.50", "Balance: 10.50"]


def test_exports():
    led, a, _ = two()
    led.deposit(a, 1050, "pay")
    assert export.accounts_csv(led).splitlines()[1].startswith("1,Ann,10.50,")
    assert export.history_csv(led, a).splitlines()[1] == "1,deposit,10.50,10.50,pay"


def test_overdraft_open_validation():
    led = Ledger()
    for bad in (-1, 1.5, True, "5"):
        with pytest.raises(ValueError):
            led.open_account("Ann", overdraft=bad)
    assert led.accounts == {}
    assert led.open_account("Ann", overdraft=300).overdraft == 300


def test_overdraft_withdraw_and_fee():
    led = Ledger()
    a = led.open_account("Ann", overdraft=300).account_id
    led.deposit(a, 100)
    led.withdraw(a, 350)  # 100 - 350 = -250, allowed; fee takes it to -750
    fees = [t for t in led.history(a) if t.kind == "fee"]
    assert [(t.amount, t.memo) for t in fees] == [(-500, "overdraft fee")]
    assert led.balance(a) == -750
    n = len(led.txns)
    with pytest.raises(InsufficientFunds):
        led.withdraw(a, 1)
    assert len(led.txns) == n


def test_overdraft_exact_zero_no_fee():
    led = Ledger()
    a = led.open_account("Ann").account_id
    led.deposit(a, 100)
    led.withdraw(a, 100)
    assert [t.kind for t in led.history(a)] == ["deposit", "withdraw"]


def test_overdraft_transfer_fee_after_transfer_in():
    led = Ledger()
    a = led.open_account("Ann", overdraft=100).account_id
    b = led.open_account("Bob").account_id
    out, inn = led.transfer(a, b, 50)
    assert (out.kind, inn.kind) == ("transfer_out", "transfer_in")
    assert [t.kind for t in led.history(a)] == ["transfer_out", "fee"]
    assert led.balance(a) == -550 and led.balance(b) == 50


def test_set_overdraft_rules():
    led, a, _ = two()
    led.deposit(a, 100)
    with pytest.raises(InsufficientFunds):
        led.withdraw(a, 150)  # no overdraft yet
    assert led.balance(a) == 100
    with pytest.raises(ValueError):
        led.set_overdraft(a, -1)
    led.set_overdraft(a, 100)
    led.withdraw(a, 150)  # 100 - 150 = -50, fee -> -550
    assert led.balance(a) == -550
    with pytest.raises(ValueError):
        led.set_overdraft(a, 549)  # below current debt
    assert led.set_overdraft(a, 550).overdraft == 550


def test_overdraft_interest_and_statement():
    led = Ledger()
    a = led.open_account("Ann", overdraft=1000).account_id
    led.deposit(a, 100)
    led.withdraw(a, 350)  # -250, fee -> -750
    posted = interest.accrue(led, 100)  # 750 * 150bp = 11.25 -> 11
    assert [(t.account_id, t.amount, t.memo) for t in posted] == [(a, -11, "overdraft interest")]
    text = statement.render(led, a)
    assert "Overdraft limit: 10.00" in text
    assert "Available: 2.39" in text
    assert text.index("Balance:") < text.index("Overdraft limit:")

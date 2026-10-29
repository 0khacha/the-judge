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

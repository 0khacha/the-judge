from datetime import date, timedelta

import pytest

from lib import Library, report
from lib.cli import main
from lib.errors import LimitError, NotAvailable

D0 = date(2024, 1, 1)


class Clock:
    def __init__(self):
        self.now = D0

    def __call__(self):
        return self.now


def make():
    clock = Clock()
    lib = Library(clock=clock)
    lib.add_book("1", "Dune", 20.0)
    lib.add_book("2", "Emma", 1.0)
    lib.add_book("3", "Ulysses", 30.0, copies=2)
    lib.add_book("4", "Hamlet", 10.0)
    lib.add_member("Ann")
    return lib, clock


def test_checkout_due():
    lib, _ = make()
    loan = lib.checkout("1", 1)
    assert loan.due == D0 + timedelta(days=14)


def test_limit():
    lib, _ = make()
    for isbn in "123":
        lib.checkout(isbn, 1)
    with pytest.raises(LimitError):
        lib.checkout("4", 1)


def test_not_available():
    lib, _ = make()
    lib.add_member("Bob")
    lib.checkout("1", 1)
    with pytest.raises(NotAvailable):
        lib.checkout("1", 2)


def test_return_on_time_no_fine():
    lib, clock = make()
    loan = lib.checkout("1", 1)
    clock.now = D0 + timedelta(days=14)
    assert lib.return_book(loan.loan_id) == 0


def test_return_late_fine():
    lib, clock = make()
    loan = lib.checkout("1", 1)
    clock.now = D0 + timedelta(days=18)
    assert lib.return_book(loan.loan_id) == 1.0
    assert lib.fines_owed[1] == 1.0


def test_fine_capped():
    lib, clock = make()
    loan = lib.checkout("2", 1)
    clock.now = D0 + timedelta(days=60)
    assert lib.return_book(loan.loan_id) == 1.0


def test_renew():
    lib, _ = make()
    loan = lib.checkout("1", 1)
    lib.renew(loan.loan_id)
    assert loan.due == D0 + timedelta(days=28)


def test_summary_basic():
    lib, _ = make()
    lib.checkout("1", 1)
    assert "Member #1: Ann" in report.member_summary(lib, 1)


def test_cli_roundtrip():
    lib = Library(clock=Clock())
    out = []
    assert main(["add-book", "9", "Zed", "5"], lib, out.append) == 0
    assert main(["add-member", "Cy"], lib, out.append) == 0
    assert main(["checkout", "9", "1"], lib, out.append) == 0
    assert out[-1] == "loan 1 due 2024-01-15"
    assert main(["checkout", "x", "1"], lib, out.append) == 1

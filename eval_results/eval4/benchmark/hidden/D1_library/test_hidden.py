from datetime import date, timedelta

import pytest

from lib import Library, report
from lib.cli import main
from lib.errors import Blocked, LibraryError, LimitError

D0 = date(2024, 1, 1)


class Clock:
    def __init__(self):
        self.now = D0

    def __call__(self):
        return self.now


def make(n_books=12):
    clock = Clock()
    lib = Library(clock=clock)
    for i in range(1, n_books + 1):
        lib.add_book(str(i), "Book%d" % i, 100.0)
    lib.add_book("cheap", "Cheap", 1.0)
    return lib, clock


def days(n):
    return D0 + timedelta(days=n)


# ---------------------------------------------------------------- new
def test_new_default_tier():
    lib, _ = make()
    assert lib.add_member("Ann").tier == "standard"


def test_new_premium_tier_stored():
    lib, _ = make()
    assert lib.add_member("Ann", tier="premium").tier == "premium"
    assert lib.members[1].tier == "premium"


def test_new_invalid_tier_rejected_without_member():
    lib, _ = make()
    with pytest.raises(ValueError):
        lib.add_member("Ann", tier="gold")
    assert lib.members == {}
    assert lib.add_member("Bob").member_id == 1


def test_new_premium_due_28_days():
    lib, _ = make()
    lib.add_member("Ann", "premium")
    assert lib.checkout("1", 1).due == days(28)


def test_new_standard_due_14_days():
    lib, _ = make()
    lib.add_member("Ann")
    assert lib.checkout("1", 1).due == days(14)


def test_new_premium_limit_10():
    lib, _ = make()
    lib.add_member("Ann", "premium")
    for i in range(1, 11):
        lib.checkout(str(i), 1)
    with pytest.raises(LimitError):
        lib.checkout("11", 1)


def test_new_standard_limit_3():
    lib, _ = make()
    lib.add_member("Ann")
    for i in range(1, 4):
        lib.checkout(str(i), 1)
    with pytest.raises(LimitError):
        lib.checkout("4", 1)


def test_new_premium_half_fine_rate():
    lib, clock = make()
    lib.add_member("Ann", "premium")
    loan = lib.checkout("1", 1)
    clock.now = days(28 + 4)
    assert lib.return_book(loan.loan_id) == 0.5
    assert lib.fines_owed[1] == 0.5


def test_new_premium_fine_capped_at_price():
    lib, clock = make()
    lib.add_member("Ann", "premium")
    loan = lib.checkout("cheap", 1)
    clock.now = days(28 + 100)
    assert lib.return_book(loan.loan_id) == 1.0


def test_new_standard_fine_unchanged():
    lib, clock = make()
    lib.add_member("Ann")
    loan = lib.checkout("1", 1)
    clock.now = days(14 + 3)
    assert lib.return_book(loan.loan_id) == 0.75


def test_new_set_tier_returns_member_and_changes_limit():
    lib, _ = make()
    lib.add_member("Ann")
    for i in range(1, 4):
        lib.checkout(str(i), 1)
    m = lib.set_tier(1, "premium")
    assert m.tier == "premium" and lib.members[1].tier == "premium"
    lib.checkout("4", 1)


def test_new_set_tier_keeps_existing_due_dates():
    lib, _ = make()
    lib.add_member("Ann")
    loan = lib.checkout("1", 1)
    lib.set_tier(1, "premium")
    assert loan.due == days(14)
    lib.set_tier(1, "standard")
    assert loan.due == days(14)


def test_new_set_tier_new_loans_use_new_tier():
    lib, _ = make()
    lib.add_member("Ann")
    lib.set_tier(1, "premium")
    assert lib.checkout("1", 1).due == days(28)


def test_new_set_tier_invalid_keeps_tier():
    lib, _ = make()
    lib.add_member("Ann", "premium")
    with pytest.raises(ValueError):
        lib.set_tier(1, "vip")
    assert lib.members[1].tier == "premium"


def test_new_set_tier_unknown_member():
    lib, _ = make()
    with pytest.raises(KeyError):
        lib.set_tier(99, "premium")


def test_new_premium_renew_28():
    lib, _ = make()
    lib.add_member("Ann", "premium")
    loan = lib.checkout("1", 1)
    lib.renew(loan.loan_id)
    assert loan.due == days(56)


def test_new_renew_uses_current_tier():
    lib, _ = make()
    lib.add_member("Ann", "premium")
    loan = lib.checkout("1", 1)
    lib.set_tier(1, "standard")
    lib.renew(loan.loan_id)
    assert loan.due == days(28 + 14)


def test_new_fine_uses_tier_at_return_time():
    lib, clock = make()
    lib.add_member("Ann", "premium")
    loan = lib.checkout("1", 1)
    lib.set_tier(1, "standard")
    clock.now = days(28 + 4)
    assert lib.return_book(loan.loan_id) == 1.0


def test_new_summary_tier_line():
    lib, _ = make()
    lib.add_member("Ann", "premium")
    lib.add_member("Bob")
    a = report.member_summary(lib, 1).split("\n")
    b = report.member_summary(lib, 2).split("\n")
    assert a[0] == "Member #1: Ann" and a[1] == "Tier: premium"
    assert b[1] == "Tier: standard"


def test_new_summary_limit_per_tier():
    lib, _ = make()
    lib.add_member("Ann", "premium")
    lib.add_member("Bob")
    lib.checkout("1", 1)
    lib.checkout("2", 1)
    lib.checkout("3", 2)
    assert "Active loans: 2/10" in report.member_summary(lib, 1)
    assert "Active loans: 1/3" in report.member_summary(lib, 2)


def test_new_overdue_report_uses_tier_rate():
    lib, clock = make()
    lib.add_member("Ann", "premium")
    lib.add_member("Bob")
    lib.checkout("1", 1)
    lib.checkout("2", 2)
    clock.now = days(28 + 4)
    text = report.overdue_report(lib)
    assert text == "Book1 | Ann | 4 days late | fine 0.50\nBook2 | Bob | 18 days late | fine 4.50"[0:0] + \
        "Book2 | Bob | 18 days late | fine 4.50\nBook1 | Ann | 4 days late | fine 0.50"


def test_new_overdue_report_premium_not_overdue_at_14():
    lib, clock = make()
    lib.add_member("Ann", "premium")
    lib.checkout("1", 1)
    clock.now = days(20)
    assert report.overdue_report(lib) == "No overdue loans."


def test_new_cli_add_member_tier():
    lib, _ = make()
    out = []
    assert main(["add-member", "Ann", "--tier", "premium"], lib, out.append) == 0
    assert out == ["member 1 Ann"]
    assert lib.members[1].tier == "premium"


def test_new_cli_add_member_bad_tier():
    lib, _ = make()
    out = []
    assert main(["add-member", "Ann", "--tier", "gold"], lib, out.append) == 1
    assert out[-1].startswith("error:")
    assert lib.members == {}


def test_new_cli_set_tier():
    lib, _ = make()
    out = []
    main(["add-member", "Ann"], lib, out.append)
    assert main(["set-tier", "1", "premium"], lib, out.append) == 0
    assert out[-1] == "member 1 tier premium"
    assert lib.members[1].tier == "premium"


def test_new_cli_set_tier_errors():
    lib, _ = make()
    out = []
    main(["add-member", "Ann"], lib, out.append)
    assert main(["set-tier", "1", "gold"], lib, out.append) == 1
    assert out[-1].startswith("error:")
    assert main(["set-tier", "7", "premium"], lib, out.append) == 1
    assert lib.members[1].tier == "standard"


# ---------------------------------------------------------------- regression
def test_reg_block_threshold_standard():
    lib, clock = make()
    lib.add_member("Ann")
    loan = lib.checkout("1", 1)
    clock.now = days(14 + 20)
    assert lib.return_book(loan.loan_id) == 5.0
    with pytest.raises(Blocked):
        lib.checkout("2", 1)


def test_reg_pay_fines_unblocks():
    lib, clock = make()
    lib.add_member("Ann")
    loan = lib.checkout("1", 1)
    clock.now = days(14 + 20)
    lib.return_book(loan.loan_id)
    assert lib.pay_fines(1, 1.0) == 4.0
    lib.checkout("2", 1)
    assert lib.pay_fines(1, 100) == 0.0
    with pytest.raises(ValueError):
        lib.pay_fines(1, 0)


def test_reg_block_threshold_premium():
    lib, clock = make()
    lib.add_member("Ann", "premium")
    loan = lib.checkout("1", 1)
    clock.now = days(28 + 40)
    assert lib.return_book(loan.loan_id) == 5.0
    with pytest.raises(Blocked):
        lib.checkout("2", 1)


def test_reg_add_book_existing_adds_copies():
    lib, _ = make()
    lib.add_book("1", "Other title", 5.0, copies=2)
    assert lib.books["1"].copies == 3
    assert lib.books["1"].title == "Book1"
    with pytest.raises(ValueError):
        lib.add_book("zz", "Z", 1.0, copies=0)


def test_reg_available_counts_loans():
    lib, _ = make()
    lib.add_book("1", "x", 1.0)
    lib.add_member("Ann")
    lib.add_member("Bob")
    lib.checkout("1", 1)
    assert lib.available("1") == 1
    lib.checkout("1", 2)
    assert lib.available("1") == 0
    with pytest.raises(KeyError):
        lib.available("nope")


def test_reg_return_twice_fails():
    lib, _ = make()
    lib.add_member("Ann")
    loan = lib.checkout("1", 1)
    lib.return_book(loan.loan_id)
    with pytest.raises(LibraryError):
        lib.return_book(loan.loan_id)
    assert lib.available("1") == 1


def test_reg_renew_only_once():
    lib, _ = make()
    lib.add_member("Ann")
    loan = lib.checkout("1", 1)
    lib.renew(loan.loan_id)
    with pytest.raises(LibraryError):
        lib.renew(loan.loan_id)
    assert loan.due == days(28)


def test_reg_premium_renew_only_once():
    lib, _ = make()
    lib.add_member("Ann", "premium")
    loan = lib.checkout("1", 1)
    lib.renew(loan.loan_id)
    with pytest.raises(LibraryError):
        lib.renew(loan.loan_id)


def test_reg_renew_overdue_fails():
    lib, clock = make()
    lib.add_member("Ann")
    loan = lib.checkout("1", 1)
    clock.now = days(15)
    with pytest.raises(LibraryError):
        lib.renew(loan.loan_id)


def test_reg_overdue_list_and_unknowns():
    lib, clock = make()
    lib.add_member("Ann")
    loan = lib.checkout("1", 1)
    assert lib.overdue() == []
    clock.now = days(14)
    assert lib.overdue() == []
    clock.now = days(15)
    assert lib.overdue() == [loan]
    with pytest.raises(KeyError):
        lib.checkout("nope", 1)
    with pytest.raises(KeyError):
        lib.checkout("1", 42)


def test_reg_add_member_blank_and_strip():
    lib, _ = make()
    with pytest.raises(ValueError):
        lib.add_member("   ")
    assert lib.add_member("  Ann ").name == "Ann"


def test_reg_overdue_report_sorted_most_late_first():
    lib, clock = make()
    lib.add_member("Ann")
    lib.add_member("Bob")
    lib.checkout("1", 1)
    clock.now = days(3)
    lib.checkout("2", 2)
    clock.now = days(25)
    lines = report.overdue_report(lib).split("\n")
    assert lines == ["Book1 | Ann | 11 days late | fine 2.75", "Book2 | Bob | 8 days late | fine 2.00"]


def test_reg_overdue_report_empty():
    lib, _ = make()
    assert report.overdue_report(lib) == "No overdue loans."


def test_reg_summary_lists_loans_and_fines():
    lib, _ = make()
    lib.add_member("Ann")
    lib.checkout("1", 1)
    lines = report.member_summary(lib, 1).split("\n")
    assert lines[2] == "Active loans: 1/3"
    assert lines[3] == "Fines owed: 0.00"
    assert lines[4] == "  - Book1 due 2024-01-15"
    with pytest.raises(KeyError):
        report.member_summary(lib, 5)


def test_reg_cli_usage_and_errors():
    lib, _ = make()
    out = []
    assert main([], lib, out.append) == 2
    assert out[-1].startswith("commands:")
    assert main(["bogus"], lib, out.append) == 2
    assert main(["add-member"], lib, out.append) == 1
    assert out[-1].startswith("error:")


def test_reg_cli_renew_and_return():
    lib, clock = make()
    out = []
    main(["add-member", "Ann"], lib, out.append)
    main(["checkout", "1", "1"], lib, out.append)
    assert main(["renew", "1"], lib, out.append) == 0
    assert out[-1] == "loan 1 due 2024-01-29"
    assert main(["return", "1"], lib, out.append) == 0
    assert out[-1] == "returned, fine 0.00"
    assert main(["return", "1"], lib, out.append) == 1


def test_reg_cli_summary_and_overdue():
    lib, clock = make()
    out = []
    main(["add-member", "Ann"], lib, out.append)
    main(["checkout", "1", "1"], lib, out.append)
    clock.now = days(16)
    main(["overdue"], lib, out.append)
    assert out[-1] == "Book1 | Ann | 2 days late | fine 0.50"
    main(["summary", "1"], lib, out.append)
    assert "Member #1: Ann" in out[-1]

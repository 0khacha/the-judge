from datetime import date, datetime

import pytest

from rooms import CapacityError, Conflict, RuleError, Scheduler
from rooms import report

DAY = date(2024, 3, 4)


def at(h, m=0):
    return datetime(2024, 3, 4, h, m)


def make():
    s = Scheduler(clock=lambda: datetime(2024, 3, 1, 12, 0))
    s.add_room("A", 6)
    s.add_room("B", 2)
    return s


def test_book_and_list():
    s = make()
    b = s.book("A", at(9), at(10), "ann", 3)
    assert b.booking_id == 1 and b.minutes == 60
    assert s.bookings(day=DAY) == [b]


def test_conflict_and_back_to_back():
    s = make()
    s.book("A", at(9), at(10), "ann")
    with pytest.raises(Conflict):
        s.book("A", at(9, 30), at(10, 30), "bob")
    s.book("A", at(10), at(11), "bob")
    s.book("B", at(9), at(10), "cy")


def test_rules_and_capacity():
    s = make()
    with pytest.raises(RuleError):
        s.book("A", at(7), at(9), "x")
    with pytest.raises(RuleError):
        s.book("A", at(9, 5), at(10), "x")
    with pytest.raises(CapacityError):
        s.book("B", at(9), at(10), "x", 3)


def test_cancel_and_reschedule():
    s = make()
    b = s.book("A", at(9), at(10), "ann")
    s.reschedule(b.booking_id, at(11), at(12))
    assert b.start == at(11)
    s.cancel(b.booking_id)
    assert s.bookings() == []


def test_free_slots():
    s = make()
    s.book("A", at(9), at(10), "ann")
    slots = s.free_slots("A", DAY, 120)
    assert at(8) not in slots and at(10) in slots and at(16) in slots and at(16, 15) not in slots


def test_find_room():
    s = make()
    s.book("A", at(9), at(10), "ann")
    assert s.find_room(at(9), at(10), 2) == "B"
    assert s.find_room(at(9), at(10), 4) is None


def test_report():
    s = make()
    s.book("A", at(9), at(10), "ann", 3)
    text = report.day_schedule(s, DAY).split("\n")
    assert text[:3] == ["Schedule for 2024-03-04", "A (cap 6)", "  09:00-10:00 ann (3)"]
    assert report.utilization(s, DAY) == {"A": 0.1, "B": 0.0}

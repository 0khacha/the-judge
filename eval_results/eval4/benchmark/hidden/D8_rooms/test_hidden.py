import copy
from datetime import date, datetime, timedelta

import pytest

from rooms import CapacityError, Conflict, RuleError, Scheduler
from rooms import report

DAY = date(2024, 3, 4)


def at(h, m=0, d=4):
    return datetime(2024, 3, d, h, m)


def make(buffer_a=0, buffer_b=0, now=datetime(2024, 3, 1, 12, 0)):
    s = Scheduler(clock=lambda: now)
    s.add_room("A", 6, buffer_a)
    s.add_room("B", 2, buffer_b)
    return s


def accepted(sched, room, start, minutes):
    probe = copy.deepcopy(sched)
    try:
        probe.book(room, start, start + timedelta(minutes=minutes), "probe")
        return True
    except (Conflict, RuleError):
        return False


# ------------------------------------------------------------------ new
def test_new_room_buffer_attribute_and_default():
    s = Scheduler()
    assert s.add_room("A", 4).buffer_minutes == 0
    assert s.add_room("B", 4, 15).buffer_minutes == 15
    assert s.add_room("C", 4, buffer_minutes=60).buffer_minutes == 60
    assert s.room("B").buffer_minutes == 15


def test_new_invalid_buffer_rejected():
    s = Scheduler()
    for bad in (-1, 61, 1.5, True, "15", None):
        with pytest.raises(ValueError):
            s.add_room("A", 4, bad)
    assert s.rooms == {}


def test_new_booking_right_after_is_blocked_by_buffer():
    s = make(15)
    s.book("A", at(9), at(10), "ann")
    with pytest.raises(Conflict):
        s.book("A", at(10), at(11), "bob")
    with pytest.raises(Conflict):
        s.book("A", at(10, 0), at(10, 30), "bob")
    s.book("A", at(10, 15), at(11), "bob")


def test_new_booking_right_before_is_blocked_by_buffer():
    s = make(15)
    s.book("A", at(10), at(11), "ann")
    with pytest.raises(Conflict):
        s.book("A", at(9), at(10), "bob")
    with pytest.raises(Conflict):
        s.book("A", at(9, 15), at(10), "bob")
    with pytest.raises(Conflict):
        s.book("A", at(9, 30), at(10), "bob")
    s.book("A", at(9), at(9, 45), "bob")


def test_new_gap_equal_to_buffer_is_fine_on_both_sides():
    s = make(15)
    s.book("A", at(10, 15), at(11, 15), "mid")
    s.book("A", at(9), at(10), "before")
    s.book("A", at(11, 30), at(12, 30), "after")
    assert [b.who for b in s.bookings(room="A")] == ["before", "mid", "after"]


def test_new_larger_buffer():
    s = make(30)
    s.book("A", at(9), at(10), "ann")
    with pytest.raises(Conflict):
        s.book("A", at(10, 15), at(11), "bob")
    s.book("A", at(10, 30), at(11), "bob")


def test_new_buffer_is_per_room():
    s = make(15, 0)
    s.book("A", at(9), at(10), "ann")
    s.book("B", at(9), at(10), "ann")
    s.book("B", at(10), at(11), "bob")
    with pytest.raises(Conflict):
        s.book("A", at(10), at(11), "bob")


def test_new_buffer_may_extend_past_closing_and_before_opening():
    s = make(60)
    s.book("A", at(17), at(18), "late")
    s.book("A", at(8), at(9), "early")
    assert len(s.bookings(room="A")) == 2


def test_new_buffer_does_not_carry_into_next_day():
    s = make(60)
    s.book("A", at(17), at(18), "late")
    s.book("A", at(8, d=5), at(9, d=5), "next day")


def test_new_cancel_releases_buffer():
    s = make(15)
    b = s.book("A", at(9), at(10), "ann")
    with pytest.raises(Conflict):
        s.book("A", at(10), at(11), "bob")
    s.cancel(b.booking_id)
    s.book("A", at(10), at(11), "bob")


def test_new_reschedule_does_not_conflict_with_itself():
    s = make(15)
    b = s.book("A", at(9), at(10), "ann")
    s.reschedule(b.booking_id, at(9, 15), at(10, 15))
    assert (b.start, b.end) == (at(9, 15), at(10, 15))
    s.reschedule(b.booking_id, at(9), at(9, 30))
    assert b.end == at(9, 30)


def test_new_reschedule_respects_buffer_of_other_bookings():
    s = make(15)
    first = s.book("A", at(9), at(10), "ann")
    s.book("A", at(10, 30), at(11, 30), "bob")
    with pytest.raises(Conflict):
        s.reschedule(first.booking_id, at(9, 30), at(10, 30))
    assert (first.start, first.end) == (at(9), at(10))
    s.reschedule(first.booking_id, at(9, 15), at(10, 15))
    with pytest.raises(Conflict):
        s.reschedule(first.booking_id, at(9, 45), at(10, 30))
    other = s.bookings(room="A")[1]
    with pytest.raises(Conflict):
        s.reschedule(other.booking_id, at(10, 15), at(11))


def test_new_free_slots_with_buffer():
    s = make(15)
    s.book("A", at(10), at(11), "ann")
    expected = [at(8), at(8, 15), at(8, 30), at(8, 45)]
    start = at(11, 15)
    while start <= at(17):
        expected.append(start)
        start += timedelta(minutes=15)
    assert s.free_slots("A", DAY, 60) == expected


def test_new_free_slots_match_book_for_every_start():
    for buf in (0, 15, 30, 60):
        s = make(buf)
        s.book("A", at(9), at(10), "x")
        s.book("A", at(12, 30), at(14), "y")
        s.book("A", at(16), at(18), "z")
        for minutes in (15, 60, 120):
            slots = set(s.free_slots("A", DAY, minutes))
            for k in range(0, 40):
                start = at(8) + timedelta(minutes=15 * k)
                assert (start in slots) == accepted(s, "A", start, minutes), (buf, minutes, start)


def test_new_free_slots_last_slot_of_day_with_buffer():
    s = make(30)
    assert s.free_slots("A", DAY, 60)[-1] == at(17)
    assert s.free_slots("A", DAY, 15)[-1] == at(17, 45)


def test_new_find_room_respects_buffer():
    s = make(15, 0)
    s.book("A", at(9), at(10), "ann")
    assert s.find_room(at(10), at(11), 2) == "B"
    assert s.find_room(at(10, 15), at(11), 2) == "A"
    s.book("B", at(10), at(10, 30), "bob")
    assert s.find_room(at(10), at(11), 2) is None


def test_new_find_room_buffer_before_booking():
    s = make(15, 15)
    s.book("A", at(10), at(11), "ann")
    s.book("B", at(10), at(10, 30), "bob")
    assert s.find_room(at(9), at(10), 2) is None
    assert s.find_room(at(9), at(9, 45), 2) == "A"


def test_new_report_header_shows_buffer():
    s = make(15, 0)
    lines = report.day_schedule(s, DAY).split("\n")
    assert lines == ["Schedule for 2024-03-04", "A (cap 6, buffer 15 min)", "  (no bookings)",
                     "B (cap 2)", "  (no bookings)"]


def test_new_utilization_ignores_buffer():
    s = make(30)
    s.book("A", at(9), at(10), "ann")
    assert report.utilization(s, DAY) == {"A": 0.1, "B": 0.0}


def test_new_other_checks_still_come_first():
    s = make(15)
    with pytest.raises(CapacityError):
        s.book("B", at(9), at(10), "x", 3)
    with pytest.raises(RuleError):
        s.book("A", at(9, 5), at(10), "x")
    with pytest.raises(RuleError):
        s.book("A", at(17, 30), at(18, 30), "x")


# ------------------------------------------------------------------ regression
def test_reg_add_room_validation():
    s = Scheduler()
    for name, cap in (("", 3), ("  ", 3), ("A", 0), ("A", 2.5)):
        with pytest.raises(ValueError):
            s.add_room(name, cap)
    s.add_room(" Big ", 10)
    assert "Big" in s.rooms
    with pytest.raises(ValueError):
        s.add_room("Big", 5)
    with pytest.raises(KeyError):
        s.room("nope")
    with pytest.raises(KeyError):
        s.book("nope", at(9), at(10), "x")
    with pytest.raises(KeyError):
        s.free_slots("nope", DAY, 60)


def test_reg_rules():
    s = make()
    bad = [(at(10), at(10)), (at(11), at(10)), (at(9), at(9, 7)), (at(7, 45), at(9)),
           (at(17), at(18, 15)), (at(9), at(13, 15)), (at(9), datetime(2024, 3, 5, 9))]
    for start, end in bad:
        with pytest.raises(RuleError):
            s.book("A", start, end, "x")
    s.book("A", at(9), at(13), "four hours")
    s.book("A", at(14), at(18), "to closing")
    s.book("A", at(13), at(13, 15), "fifteen")


def test_reg_seconds_rejected():
    s = make()
    with pytest.raises(RuleError):
        s.book("A", datetime(2024, 3, 4, 9, 0, 30), at(10), "x")


def test_reg_past_start_rejected_but_now_allowed():
    s = make(now=at(9))
    with pytest.raises(RuleError):
        s.book("A", at(8, 45), at(9, 30), "x")
    s.book("A", at(9), at(9, 30), "x")


def test_reg_capacity_limits():
    s = make()
    for n in (0, -1, 7):
        with pytest.raises(CapacityError):
            s.book("A", at(9), at(10), "x", n)
    s.book("A", at(9), at(10), "x", 6)


def test_reg_conflict_shapes():
    s = make()
    s.book("A", at(10), at(12), "ann")
    for start, end in ((at(9), at(10, 15)), (at(11, 45), at(13)), (at(10, 30), at(11)), (at(9), at(13)), (at(10), at(12))):
        with pytest.raises(Conflict):
            s.book("A", start, end, "bob")
    s.book("A", at(8), at(10), "before")
    s.book("A", at(12), at(13), "after")


def test_reg_back_to_back_allowed_without_buffer():
    s = make()
    s.book("A", at(9), at(10), "a")
    s.book("A", at(10), at(11), "b")
    s.book("A", at(8), at(9), "c")


def test_reg_cancel_rules():
    s = make(now=datetime(2024, 3, 4, 9, 30))
    s.add_room("C", 3)
    future = s.book("C", at(11), at(12), "f")
    s._bookings[99] = type(future)(99, "C", at(9), at(10), "started")
    with pytest.raises(RuleError):
        s.cancel(99)
    assert s.cancel(future.booking_id) is future
    with pytest.raises(KeyError):
        s.cancel(12345)


def test_reg_reschedule_overlapping_own_old_slot():
    s = make()
    b = s.book("A", at(9), at(11), "ann")
    s.reschedule(b.booking_id, at(10), at(12))
    assert (b.start, b.end) == (at(10), at(12))
    s.reschedule(b.booking_id, at(9), at(10))
    assert b.minutes == 60


def test_reg_reschedule_failures_leave_booking_alone():
    s = make()
    b = s.book("A", at(9), at(10), "ann")
    s.book("A", at(11), at(12), "bob")
    with pytest.raises(Conflict):
        s.reschedule(b.booking_id, at(10, 30), at(11, 30))
    with pytest.raises(RuleError):
        s.reschedule(b.booking_id, at(9, 10), at(10))
    with pytest.raises(KeyError):
        s.reschedule(404, at(9), at(10))
    assert (b.start, b.end) == (at(9), at(10))


def test_reg_bookings_listing():
    s = make()
    b3 = s.book("B", at(9), at(10), "c")
    b1 = s.book("A", at(11), at(12), "a")
    b2 = s.book("A", at(9), at(10), "b")
    b4 = s.book("A", at(9, d=5), at(10, d=5), "d")
    assert s.bookings() == [b3, b2, b1, b4]
    assert s.bookings(day=DAY) == sorted([b1, b2, b3], key=lambda b: (b.start, b.booking_id))
    assert s.bookings(room="A", day=DAY) == [b2, b1]
    assert s.bookings(room="B") == [b3]


def test_reg_free_slots_without_buffer():
    s = make()
    s.book("A", at(9), at(10), "ann")
    slots = s.free_slots("A", DAY, 60)
    for blocked in (at(8, 15), at(8, 30), at(8, 45), at(9), at(9, 15), at(9, 30), at(9, 45)):
        assert blocked not in slots
    assert at(8) in slots and at(10) in slots and slots[-1] == at(17)
    assert s.free_slots("A", DAY, 300) == []
    assert s.free_slots("B", DAY, 60)[0] == at(8)


def test_reg_free_slots_exclude_past():
    s = make(now=at(12))
    slots = s.free_slots("A", DAY, 60)
    assert slots[0] == at(12) and slots[-1] == at(17)


def test_reg_find_room_rules():
    s = make()
    assert s.find_room(at(9), at(10), 1) == "A"
    assert s.find_room(at(9), at(10), 3) == "A"
    assert s.find_room(at(9), at(10), 7) is None
    s.book("A", at(9), at(10), "x")
    assert s.find_room(at(9), at(10), 2) == "B"
    s.book("B", at(9, 30), at(10), "y")
    assert s.find_room(at(9), at(10), 1) is None
    with pytest.raises(RuleError):
        s.find_room(at(9, 5), at(10), 1)


def test_reg_day_schedule_format():
    s = make()
    s.book("A", at(10), at(11), "bob", 2)
    s.book("A", at(9), at(10), "ann", 3)
    assert report.day_schedule(s, DAY) == "\n".join([
        "Schedule for 2024-03-04", "A (cap 6)", "  09:00-10:00 ann (3)", "  10:00-11:00 bob (2)",
        "B (cap 2)", "  (no bookings)"])


def test_reg_utilization_values():
    s = make()
    s.book("A", at(9), at(11), "ann")
    s.book("A", at(13), at(14), "bob")
    s.book("B", at(9, d=5), at(10, d=5), "other day")
    u = report.utilization(s, DAY)
    assert u["A"] == pytest.approx(0.3) and u["B"] == 0.0

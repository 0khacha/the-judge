from datetime import date

import pytest

from tracker import BlockedError, TaskStore, storage, views
from tracker.cli import main

D = date(2024, 1, 10)


def make():
    return TaskStore(clock=lambda: D)


def test_add_and_get():
    s = make()
    t = s.add("Write", due=date(2024, 1, 12), tags=["b", "a"])
    assert s.get(t.id).tags == ["a", "b"]


def test_complete_sets_done_on():
    s = make()
    t = s.add("x")
    s.complete(t.id)
    assert t.status == "done" and t.done_on == D


def test_blocked_by_dependency():
    s = make()
    a = s.add("a")
    b = s.add("b", deps=[a.id])
    with pytest.raises(BlockedError):
        s.complete(b.id)
    s.complete(a.id)
    s.complete(b.id)


def test_ready_and_overdue():
    s = make()
    a = s.add("a", due=date(2024, 1, 1))
    s.add("b", deps=[a.id])
    assert [t.title for t in s.ready()] == ["a"]
    assert [t.title for t in s.overdue()] == ["a"]


def test_delete_needed():
    s = make()
    a = s.add("a")
    s.add("b", deps=[a.id])
    with pytest.raises(ValueError):
        s.delete(a.id)


def test_roundtrip():
    s = make()
    a = s.add("a", due=date(2024, 2, 2))
    s.complete(a.id)
    s2 = storage.load(storage.dump(s), clock=lambda: D)
    assert s2.get(1).done_on == D and s2.add("n").id == 2


def test_agenda():
    s = make()
    s.add("late", due=date(2024, 1, 5))
    text = views.agenda(s)
    assert "#1 [P2] late (due 2024-01-05) OVERDUE" in text


def test_cli():
    s = make()
    out = []
    assert main(["add", "Hello", "--due", "2024-01-11"], s, out.append) == 0
    assert main(["done", "1"], s, out.append) == 0
    assert out == ["added #1", "done #1"]
    assert main(["done", "9"], s, out.append) == 1


def test_repeat_validation_creates_nothing():
    s = make()
    with pytest.raises(ValueError):
        s.add("x", due=date(2024, 1, 1), repeat="yearly")
    with pytest.raises(ValueError):
        s.add("x", repeat="weekly")
    assert s.add("ok").id == 1


def test_complete_recurring_creates_next():
    s = make()
    t = s.add("Water", due=date(2024, 1, 31), priority=3, tags=["home"], repeat="monthly")
    done = s.complete(t.id)
    assert done is t and t.status == "done" and t.next_id == 2
    n = s.get(2)
    assert (n.title, n.due, n.priority, n.tags, n.repeat, n.status) == (
        "Water", date(2024, 2, 29), 3, ["home"], "monthly", "open")
    assert n.tags is not t.tags


def test_next_due_rules():
    from tracker.store import next_due
    assert next_due(date(2024, 2, 10), "daily") == date(2024, 2, 11)
    assert next_due(date(2024, 2, 28), "weekly") == date(2024, 3, 6)
    assert next_due(date(2024, 3, 31), "monthly") == date(2024, 4, 30)
    assert next_due(date(2024, 12, 15), "monthly") == date(2025, 1, 15)


def test_reopen_blocked_by_open_successor_and_delete_clears_link():
    s = make()
    t = s.add("w", due=date(2024, 1, 1), repeat="daily")
    s.complete(t.id)
    with pytest.raises(ValueError):
        s.reopen(t.id)
    s.delete(t.next_id)
    assert t.next_id is None
    s.reopen(t.id)
    assert t.status == "open" and t.next_id is None


def test_storage_roundtrip_and_old_format():
    s = make()
    t = s.add("w", due=date(2024, 1, 1), repeat="weekly")
    s.complete(t.id)
    data = storage.dump(s)
    assert data["tasks"][0]["next_id"] == 2 and data["tasks"][0]["repeat"] == "weekly"
    s2 = storage.load(data, clock=lambda: D)
    assert s2.get(1).next_id == 2 and s2.get(2).repeat == "weekly"
    old = {"tasks": [{"id": 1, "title": "a"}]}
    assert storage.load(old, clock=lambda: D).get(1).repeat is None


def test_agenda_and_cli_repeat():
    s = make()
    s.add("Water plants", due=date(2024, 1, 5), repeat="weekly")
    assert "#1 [P2] Water plants (due 2024-01-05) (repeats weekly) OVERDUE" in views.agenda(s)
    out = []
    assert main(["add", "Chore", "--due", "2024-01-11", "--repeat", "daily"], s, out.append) == 0
    assert main(["done", "2"], s, out.append) == 0
    assert out[-2:] == ["done #2", "next #3 due 2024-01-12"]
    out.clear()
    assert main(["list"], s, out.append) == 0
    assert out[-1].endswith(" repeat daily")
    out.clear()
    assert main(["add", "Bad", "--repeat", "daily"], s, out.append) == 1
    assert main(["add", "Bad", "--due", "2024-01-11", "--repeat", "hourly"], s, out.append) == 1
    assert all(line.startswith("error: ") for line in out)

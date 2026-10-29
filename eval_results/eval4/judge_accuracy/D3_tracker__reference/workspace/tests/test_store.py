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

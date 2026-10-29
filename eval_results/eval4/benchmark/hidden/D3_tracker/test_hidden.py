from datetime import date

import pytest

from tracker import BlockedError, TaskStore, storage, views
from tracker.cli import main


class Clock:
    def __init__(self, d=date(2024, 1, 10)):
        self.now = d

    def __call__(self):
        return self.now


def make():
    c = Clock()
    return TaskStore(clock=c), c


def d(m, day, y=2024):
    return date(y, m, day)


# ---------------------------------------------------------------- new
def test_new_defaults():
    s, _ = make()
    t = s.add("x", due=d(1, 20))
    assert t.repeat is None and t.next_id is None


def test_new_invalid_repeat_rejected_and_no_id_used():
    s, _ = make()
    with pytest.raises(ValueError):
        s.add("x", due=d(1, 20), repeat="yearly")
    assert s.tasks() == []
    assert s.add("y").id == 1


def test_new_repeat_needs_due():
    s, _ = make()
    with pytest.raises(ValueError):
        s.add("x", repeat="daily")
    assert s.tasks() == []
    assert s.add("y").id == 1


def test_new_weekly_spawns_plus_7():
    s, _ = make()
    t = s.add("Water", due=d(1, 12), repeat="weekly")
    s.complete(t.id)
    nxt = s.get(2)
    assert nxt.due == d(1, 19) and nxt.status == "open" and nxt.repeat == "weekly"


def test_new_daily_plus_1():
    s, _ = make()
    t = s.add("x", due=d(1, 31), repeat="daily")
    s.complete(t.id)
    assert s.get(2).due == d(2, 1)


def test_new_monthly_same_day():
    s, _ = make()
    t = s.add("x", due=d(1, 15), repeat="monthly")
    s.complete(t.id)
    assert s.get(2).due == d(2, 15)


def test_new_monthly_clamps_to_month_end():
    s, _ = make()
    t = s.add("x", due=d(1, 31), repeat="monthly")
    s.complete(t.id)
    assert s.get(2).due == d(2, 29)
    t2 = s.add("y", due=d(3, 31), repeat="monthly")
    s.complete(t2.id)
    assert s.get(4).due == d(4, 30)


def test_new_monthly_december_rolls_year():
    s, _ = make()
    t = s.add("x", due=d(12, 15, 2024), repeat="monthly")
    s.complete(t.id)
    assert s.get(2).due == date(2025, 1, 15)


def test_new_monthly_clamp_not_sticky_from_old_due():
    s, _ = make()
    t = s.add("x", due=d(2, 29), repeat="monthly")
    s.complete(t.id)
    assert s.get(2).due == d(3, 29)


def test_new_due_computed_from_old_due_not_completion_date():
    s, c = make()
    t = s.add("x", due=d(1, 5), repeat="weekly")
    c.now = d(1, 20)
    s.complete(t.id)
    nxt = s.get(2)
    assert nxt.due == d(1, 12)
    assert nxt in s.overdue()


def test_new_spawn_copies_fields():
    s, _ = make()
    a = s.add("dep")
    s.complete(a.id)
    t = s.add("Chore", due=d(1, 12), priority=3, tags=["home", "a"], deps=[a.id], repeat="daily")
    s.complete(t.id)
    n = s.get(3)
    assert n.title == "Chore" and n.priority == 3
    assert n.tags == ["a", "home"] and n.deps == [] and n.done_on is None


def test_new_spawn_tags_are_a_copy():
    s, _ = make()
    t = s.add("x", due=d(1, 12), tags=["a"], repeat="daily")
    s.complete(t.id)
    t.tags.append("zzz")
    assert s.get(2).tags == ["a"]


def test_new_complete_returns_completed_task_with_next_id():
    s, _ = make()
    t = s.add("x", due=d(1, 12), repeat="weekly")
    res = s.complete(t.id)
    assert res is t and res.status == "done" and res.next_id == 2


def test_new_non_recurring_creates_nothing():
    s, _ = make()
    t = s.add("x", due=d(1, 12))
    s.complete(t.id)
    assert len(s.tasks()) == 1 and t.next_id is None


def test_new_second_complete_fails_without_spawn():
    s, _ = make()
    t = s.add("x", due=d(1, 12), repeat="weekly")
    s.complete(t.id)
    with pytest.raises(ValueError):
        s.complete(t.id)
    assert len(s.tasks()) == 2


def test_new_blocked_complete_does_not_spawn():
    s, _ = make()
    a = s.add("a")
    t = s.add("x", due=d(1, 12), deps=[a.id], repeat="weekly")
    with pytest.raises(BlockedError):
        s.complete(t.id)
    assert len(s.tasks()) == 2 and t.next_id is None and t.is_open


def test_new_chain_and_id_counter():
    s, _ = make()
    t = s.add("x", due=d(1, 12), repeat="weekly")
    s.complete(t.id)
    s.complete(2)
    assert s.get(3).due == d(1, 26)
    assert s.add("after").id == 4


def test_new_dependents_of_recurring_task_are_released():
    s, _ = make()
    t = s.add("x", due=d(1, 12), repeat="weekly")
    b = s.add("b", deps=[t.id])
    s.complete(t.id)
    assert b in s.ready()
    s.complete(b.id)


def test_new_reopen_blocked_by_open_successor():
    s, _ = make()
    t = s.add("x", due=d(1, 12), repeat="weekly")
    s.complete(t.id)
    with pytest.raises(ValueError):
        s.reopen(t.id)
    assert t.status == "done" and t.next_id == 2 and t.done_on == d(1, 10)


def test_new_reopen_allowed_after_successor_done_and_resets_next_id():
    s, _ = make()
    t = s.add("x", due=d(1, 12), repeat="weekly")
    s.complete(t.id)
    s.complete(2)
    s.reopen(t.id)
    assert t.is_open and t.next_id is None and t.done_on is None


def test_new_delete_successor_clears_next_id():
    s, _ = make()
    t = s.add("x", due=d(1, 12), repeat="weekly")
    s.complete(t.id)
    s.delete(2)
    assert t.next_id is None
    s.reopen(t.id)


def test_new_storage_dump_has_keys():
    s, _ = make()
    s.add("plain")
    t = s.add("x", due=d(1, 12), repeat="weekly")
    s.complete(t.id)
    data = storage.dump(s)
    by_id = {x["id"]: x for x in data["tasks"]}
    assert by_id[1]["repeat"] is None and by_id[1]["next_id"] is None
    assert by_id[2]["repeat"] == "weekly" and by_id[2]["next_id"] == 3
    assert by_id[3]["repeat"] == "weekly" and by_id[3]["next_id"] is None


def test_new_storage_roundtrip():
    s, c = make()
    t = s.add("x", due=d(1, 12), repeat="monthly")
    s.complete(t.id)
    s2 = storage.load(storage.dump(s), clock=c)
    assert s2.get(1).next_id == 2 and s2.get(2).repeat == "monthly"
    s2.complete(2)
    assert s2.get(3).due == d(3, 12)


def test_new_storage_loads_old_data():
    old = {"next_id": 2, "tasks": [{"id": 1, "title": "old", "due": "2024-01-12", "priority": 2,
                                     "tags": [], "deps": [], "status": "open", "done_on": None}]}
    s = storage.load(old, clock=Clock())
    t = s.get(1)
    assert t.repeat is None and t.next_id is None
    s.complete(1)
    assert len(s.tasks()) == 1


def test_new_agenda_repeat_suffix_and_overdue_order():
    s, _ = make()
    s.add("Water plants", due=d(1, 12), repeat="weekly")
    s.add("Late", due=d(1, 5), repeat="daily")
    s.add("Plain", due=d(1, 11))
    lines = views.agenda(s).split("\n")
    assert lines[1:] == [
        "  #2 [P2] Late (due 2024-01-05) (repeats daily) OVERDUE",
        "  #3 [P2] Plain (due 2024-01-11)",
        "  #1 [P2] Water plants (due 2024-01-12) (repeats weekly)"]


def test_new_cli_add_repeat():
    s, _ = make()
    out = []
    assert main(["add", "Water", "--due", "2024-01-12", "--repeat", "weekly"], s, out.append) == 0
    assert s.get(1).repeat == "weekly"
    assert main(["add", "Bad", "--due", "2024-01-12", "--repeat", "yearly"], s, out.append) == 1
    assert out[-1].startswith("error:")
    assert main(["add", "NoDue", "--repeat", "daily"], s, out.append) == 1
    assert len(s.tasks()) == 1


def test_new_cli_done_prints_next():
    s, _ = make()
    out = []
    main(["add", "Water", "--due", "2024-01-12", "--repeat", "weekly"], s, out.append)
    out.clear()
    assert main(["done", "1"], s, out.append) == 0
    assert out == ["done #1", "next #2 due 2024-01-19"]


def test_new_cli_done_plain_single_line():
    s, _ = make()
    out = []
    main(["add", "x"], s, out.append)
    out.clear()
    main(["done", "1"], s, out.append)
    assert out == ["done #1"]


def test_new_cli_list_and_ready_repeat_suffix():
    s, _ = make()
    out = []
    main(["add", "Water", "--due", "2024-01-12", "--repeat", "weekly"], s, out.append)
    main(["add", "Plain", "--due", "2024-01-13"], s, out.append)
    out.clear()
    main(["list"], s, out.append)
    assert out == ["#1 [open] P2 Water due 2024-01-12 repeat weekly", "#2 [open] P2 Plain due 2024-01-13"]
    out.clear()
    main(["ready"], s, out.append)
    assert out[0].endswith(" repeat weekly") and not out[1].endswith("weekly")


def test_new_summary_counts_spawned():
    s, _ = make()
    t = s.add("x", due=d(1, 1), repeat="weekly")
    s.complete(t.id)
    assert views.summary(s) == "open: 1, done: 1, overdue: 1"


# ---------------------------------------------------------------- regression
def test_reg_add_validation():
    s, _ = make()
    with pytest.raises(ValueError):
        s.add("   ")
    with pytest.raises(ValueError):
        s.add("x", priority=4)
    with pytest.raises(ValueError):
        s.add("x", deps=[5])
    assert s.add("  Trim  ").title == "Trim"


def test_reg_tags_and_deps_normalised():
    s, _ = make()
    a = s.add("a")
    b = s.add("b")
    t = s.add("c", tags=["z", "a", "z"], deps=[b.id, a.id, a.id])
    assert t.tags == ["a", "z"] and t.deps == [1, 2]


def test_reg_complete_and_reopen_basics():
    s, c = make()
    t = s.add("x")
    c.now = d(1, 11)
    s.complete(t.id)
    assert t.done_on == d(1, 11)
    with pytest.raises(ValueError):
        s.complete(t.id)
    s.reopen(t.id)
    assert t.is_open and t.done_on is None
    with pytest.raises(ValueError):
        s.reopen(t.id)


def test_reg_delete_detaches_done_dependency():
    s, _ = make()
    a = s.add("a")
    b = s.add("b", deps=[a.id])
    s.complete(a.id)
    s.complete(b.id)
    s.delete(a.id)
    assert b.deps == []
    with pytest.raises(KeyError):
        s.get(a.id)


def test_reg_delete_blocked_and_unknown():
    s, _ = make()
    a = s.add("a")
    s.add("b", deps=[a.id])
    with pytest.raises(ValueError):
        s.delete(a.id)
    with pytest.raises(KeyError):
        s.delete(77)
    assert s.get(a.id)


def test_reg_ordering():
    s, _ = make()
    s.add("nodue-p3", priority=3)
    s.add("late", due=d(2, 1))
    s.add("early-p1", due=d(1, 20), priority=1)
    s.add("early-p3", due=d(1, 20), priority=3)
    s.add("early-p3b", due=d(1, 20), priority=3)
    assert [t.title for t in s.tasks()] == ["early-p3", "early-p3b", "early-p1", "late", "nodue-p3"]


def test_reg_filters():
    s, _ = make()
    a = s.add("a", tags=["x"])
    s.add("b", tags=["y"])
    s.complete(a.id)
    assert [t.title for t in s.tasks(status="done")] == ["a"]
    assert [t.title for t in s.tasks(tag="y")] == ["b"]
    assert s.tasks(status="open", tag="x") == []


def test_reg_overdue_is_strict():
    s, c = make()
    s.add("today", due=d(1, 10))
    s.add("yesterday", due=d(1, 9))
    s.add("none")
    assert [t.title for t in s.overdue()] == ["yesterday"]


def test_reg_ready_excludes_blocked():
    s, _ = make()
    a = s.add("a")
    b = s.add("b", deps=[a.id])
    assert [t.title for t in s.ready()] == ["a"]
    s.complete(a.id)
    assert [t.title for t in s.ready()] == ["b"]


def test_reg_agenda_exact():
    s, _ = make()
    s.add("Soon", due=d(1, 12), priority=3)
    s.add("Late", due=d(1, 5))
    s.add("Far", due=d(3, 1))
    s.add("NoDue")
    assert views.agenda(s) == "\n".join([
        "Agenda for 2024-01-10 (next 7 days)",
        "  #2 [P2] Late (due 2024-01-05) OVERDUE",
        "  #1 [P3] Soon (due 2024-01-12)"])
    assert views.agenda(s, days=100).split("\n")[-1] == "  #3 [P2] Far (due 2024-03-01)"


def test_reg_agenda_empty_and_summary():
    s, _ = make()
    assert views.agenda(s, 3) == "Agenda for 2024-01-10 (next 3 days)\n  nothing due"
    assert views.summary(s) == "open: 0, done: 0, overdue: 0"


def test_reg_storage_roundtrip_keeps_counter():
    s, c = make()
    s.add("a", due=d(1, 12), tags=["t"], priority=3)
    b = s.add("b", deps=[1])
    s.delete(b.id)
    s2 = storage.load(storage.dump(s), clock=c)
    t = s2.get(1)
    assert t.due == d(1, 12) and t.tags == ["t"] and t.priority == 3
    assert s2.add("n").id == 3


def test_reg_storage_dict_basic_keys():
    s, _ = make()
    s.add("a", due=d(1, 12))
    data = storage.dump(s)
    assert data["next_id"] == 2
    item = data["tasks"][0]
    for k in ("id", "title", "due", "priority", "tags", "deps", "status", "done_on"):
        assert k in item
    assert item["due"] == "2024-01-12"


def test_reg_cli_options_and_list():
    s, _ = make()
    out = []
    assert main(["add", "A", "--tag", "x", "--tag", "y", "--prio", "3", "--due", "2024-01-12"], s, out.append) == 0
    assert main(["add", "B", "--dep", "1"], s, out.append) == 0
    assert s.get(1).tags == ["x", "y"] and s.get(2).deps == [1]
    out.clear()
    main(["list"], s, out.append)
    assert out == ["#1 [open] P3 A due 2024-01-12", "#2 [open] P2 B due -"]
    out.clear()
    main(["list", "--tag", "x"], s, out.append)
    assert out == ["#1 [open] P3 A due 2024-01-12"]


def test_reg_cli_errors_and_usage():
    s, _ = make()
    out = []
    assert main([], s, out.append) == 2
    assert main(["nope"], s, out.append) == 2
    assert main(["add"], s, out.append) == 1
    assert main(["add", "x", "--due"], s, out.append) == 1
    assert main(["done", "5"], s, out.append) == 1
    main(["add", "a"], s, out.append)
    main(["add", "b", "--dep", "1"], s, out.append)
    assert main(["done", "2"], s, out.append) == 1
    assert main(["rm", "1"], s, out.append) == 1


def test_reg_cli_reopen_rm_summary_agenda():
    s, _ = make()
    out = []
    main(["add", "a", "--due", "2024-01-11"], s, out.append)
    main(["done", "1"], s, out.append)
    out.clear()
    assert main(["reopen", "1"], s, out.append) == 0
    assert out == ["reopened #1"]
    main(["summary"], s, out.append)
    assert out[-1] == "open: 1, done: 0, overdue: 0"
    main(["agenda", "--days", "2"], s, out.append)
    assert out[-1] == "Agenda for 2024-01-10 (next 2 days)\n  #1 [P2] a (due 2024-01-11)"
    assert main(["rm", "1"], s, out.append) == 0
    assert out[-1] == "removed #1"

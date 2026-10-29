import pytest
from workflow import Workflow, InvalidTransition


def make(*steps):
    w = Workflow()
    for s in steps:
        if isinstance(s, tuple):
            w.apply(s[0], **s[1])
        else:
            w.apply(s)
    return w


A = ("assign", {"user": "ann"})
IN_PROGRESS = [A, "start"]
DONE = [A, "start", "complete"]
CLOSED = DONE + ["close"]
BLOCKED = [A, "start", ("block", {"reason": "waiting"})]
REOPENED = DONE + ["reopen"]
CANCELLED = [A, "cancel"]

STATES = {
    "NEW": [], "ASSIGNED": [A], "IN_PROGRESS": IN_PROGRESS, "BLOCKED": BLOCKED, "DONE": DONE,
    "CLOSED": CLOSED, "REOPENED": REOPENED, "CANCELLED": CANCELLED,
}


@pytest.mark.parametrize("state", list(STATES))
def test_reaching_states(state):
    assert make(*STATES[state]).state == state


def test_initial():
    w = Workflow()
    assert (w.state, w.assignee, w.block_reason, w.reopen_count, w.history) == ("NEW", None, None, 0, [])


# (state, event, kwargs) -> expected new state, or None for InvalidTransition
KW = {"assign": {"user": "bob"}, "block": {"reason": "r"}}
VALID = {
    ("NEW", "assign"): "ASSIGNED", ("ASSIGNED", "assign"): "ASSIGNED", ("REOPENED", "assign"): "ASSIGNED",
    ("ASSIGNED", "start"): "IN_PROGRESS", ("REOPENED", "start"): "IN_PROGRESS",
    ("ASSIGNED", "block"): "BLOCKED", ("IN_PROGRESS", "block"): "BLOCKED",
    ("BLOCKED", "unblock"): "IN_PROGRESS", ("IN_PROGRESS", "complete"): "DONE",
    ("DONE", "close"): "CLOSED", ("DONE", "reopen"): "REOPENED", ("CLOSED", "reopen"): "REOPENED",
    ("NEW", "cancel"): "CANCELLED", ("ASSIGNED", "cancel"): "CANCELLED", ("IN_PROGRESS", "cancel"): "CANCELLED",
    ("BLOCKED", "cancel"): "CANCELLED", ("DONE", "cancel"): "CANCELLED", ("REOPENED", "cancel"): "CANCELLED",
}
CASES = [(s, e) for s in STATES for e in ("assign", "start", "block", "unblock", "complete", "close", "reopen", "cancel")]


@pytest.mark.parametrize("state,event", CASES)
def test_transition_table(state, event):
    w = make(*STATES[state])
    before = (w.state, w.assignee, w.history, w.reopen_count, w.block_reason)
    exp = VALID.get((state, event))
    if exp is None:
        with pytest.raises(InvalidTransition):
            w.apply(event, **KW.get(event, {}))
        assert (w.state, w.assignee, w.history, w.reopen_count, w.block_reason) == before
    else:
        assert w.apply(event, **KW.get(event, {})) == exp
        assert w.state == exp


def test_assign_sets_assignee_and_reassign():
    w = make(A)
    assert w.assignee == "ann"
    w.apply("assign", user="bob")
    assert w.assignee == "bob" and w.state == "ASSIGNED"


def test_assign_same_user_in_assigned_invalid():
    w = make(A)
    with pytest.raises(InvalidTransition):
        w.apply("assign", user="ann")
    assert w.history == [("NEW", "assign", "ASSIGNED")]


def test_assign_same_user_ok_from_reopened():
    w = make(*REOPENED)
    assert w.apply("assign", user="ann") == "ASSIGNED"


@pytest.mark.parametrize("kw", [{}, {"user": ""}, {"user": "   "}, {"user": None}, {"user": 5}])
def test_assign_requires_user(kw):
    w = Workflow()
    with pytest.raises(ValueError):
        w.apply("assign", **kw)
    assert w.state == "NEW" and w.assignee is None and w.history == []


@pytest.mark.parametrize("kw", [{}, {"reason": ""}, {"reason": " \t"}, {"reason": None}])
def test_block_requires_reason(kw):
    w = make(*IN_PROGRESS)
    with pytest.raises(ValueError):
        w.apply("block", **kw)
    assert w.state == "IN_PROGRESS" and w.block_reason is None


def test_error_precedence_state_before_arguments():
    w = make(*DONE)
    with pytest.raises(InvalidTransition):
        w.apply("assign")
    with pytest.raises(InvalidTransition):
        w.apply("block")
    w2 = make(A)
    with pytest.raises(InvalidTransition):
        w2.apply("assign", user="ann")


def test_unknown_event_is_value_error_first():
    w = make(*DONE)
    with pytest.raises(ValueError) as ei:
        w.apply("explode")
    assert not isinstance(ei.value, InvalidTransition)
    with pytest.raises(ValueError):
        w.apply("ASSIGN", user="x")


def test_extra_kwargs_ignored():
    w = Workflow()
    assert w.apply("assign", user="a", colour="red") == "ASSIGNED"
    assert w.apply("start", anything=1) == "IN_PROGRESS"


def test_unblock_returns_to_origin_state():
    w = make(A, ("block", {"reason": "x"}))
    assert w.state == "BLOCKED"
    assert w.apply("unblock") == "ASSIGNED"
    w2 = make(*BLOCKED)
    assert w2.apply("unblock") == "IN_PROGRESS"


def test_block_reason_lifecycle():
    w = make(*BLOCKED)
    assert w.block_reason == "waiting"
    w.apply("unblock")
    assert w.block_reason is None
    w.apply("block", reason="again")
    assert w.block_reason == "again"
    w.apply("cancel")
    assert w.block_reason is None


def test_reopen_limit():
    w = make(*DONE)
    w.apply("reopen")
    assert w.reopen_count == 1
    w.apply("start"); w.apply("complete"); w.apply("close")
    w.apply("reopen")
    assert w.reopen_count == 2
    w.apply("start"); w.apply("complete")
    assert "reopen" not in w.allowed_events()
    with pytest.raises(InvalidTransition):
        w.apply("reopen")
    assert w.reopen_count == 2 and w.state == "DONE"
    w.apply("close")
    with pytest.raises(InvalidTransition):
        w.apply("reopen")


def test_cancel_is_terminal():
    w = make(*CANCELLED)
    assert w.allowed_events() == []
    for e in ("assign", "start", "block", "unblock", "complete", "close", "reopen", "cancel"):
        with pytest.raises(InvalidTransition):
            w.apply(e, user="x", reason="y")
    assert w.assignee == "ann"


def test_closed_cannot_cancel_but_can_reopen():
    w = make(*CLOSED)
    assert w.allowed_events() == ["reopen"]


def test_cancel_with_and_without_reason():
    assert make(A, ("cancel", {"reason": "dup"})).state == "CANCELLED"
    assert make("cancel").state == "CANCELLED"


@pytest.mark.parametrize("state,expected", [
    ("NEW", ["assign", "cancel"]),
    ("ASSIGNED", ["assign", "block", "cancel", "start"]),
    ("IN_PROGRESS", ["block", "cancel", "complete"]),
    ("BLOCKED", ["cancel", "unblock"]),
    ("DONE", ["cancel", "close", "reopen"]),
    ("CLOSED", ["reopen"]),
    ("REOPENED", ["assign", "cancel", "start"]),
    ("CANCELLED", []),
])
def test_allowed_events(state, expected):
    assert make(*STATES[state]).allowed_events() == expected


def test_history_is_a_copy_and_ordered():
    w = make(*IN_PROGRESS)
    h = w.history
    assert h == [("NEW", "assign", "ASSIGNED"), ("ASSIGNED", "start", "IN_PROGRESS")]
    h.append("junk")
    assert len(w.history) == 2
    with pytest.raises(InvalidTransition):
        w.apply("close")
    assert len(w.history) == 2


def test_listeners_order_and_args():
    w = Workflow()
    calls = []
    w.on_transition(lambda a, e, b: calls.append(("1", a, e, b, w.state, len(w.history))))
    w.on_transition(lambda a, e, b: calls.append(("2", a, e, b)))
    w.apply("assign", user="u")
    assert calls == [("1", "NEW", "assign", "ASSIGNED", "ASSIGNED", 1), ("2", "NEW", "assign", "ASSIGNED")]


def test_listeners_not_called_on_failure_or_undo():
    w = Workflow()
    calls = []
    w.on_transition(lambda *a: calls.append(a))
    with pytest.raises(InvalidTransition):
        w.apply("start")
    with pytest.raises(ValueError):
        w.apply("assign")
    w.apply("assign", user="u")
    w.undo()
    assert len(calls) == 1


def test_listener_exception_keeps_transition_and_stops_chain():
    w = Workflow()
    later = []

    def boom(a, e, b):
        raise RuntimeError("x")

    w.on_transition(boom)
    w.on_transition(lambda *a: later.append(a))
    with pytest.raises(RuntimeError):
        w.apply("assign", user="u")
    assert w.state == "ASSIGNED" and w.assignee == "u"
    assert w.history == [("NEW", "assign", "ASSIGNED")]
    assert later == []
    assert w.undo() == "NEW"


def test_undo_basic_and_repeated():
    w = make(*DONE)
    assert w.undo() == "IN_PROGRESS"
    assert w.undo() == "ASSIGNED"
    assert w.undo() == "NEW"
    assert w.assignee is None
    assert w.history == []
    with pytest.raises(InvalidTransition):
        w.undo()


def test_undo_restores_assignee():
    w = make(A)
    w.apply("assign", user="bob")
    w.undo()
    assert w.assignee == "ann" and w.state == "ASSIGNED"


def test_undo_restores_reopen_count():
    w = make(*REOPENED)
    assert w.reopen_count == 1
    assert w.undo() == "DONE"
    assert w.reopen_count == 0
    w.apply("reopen"); w.apply("start"); w.apply("complete"); w.apply("reopen")
    w.apply("start"); w.apply("complete")
    assert "reopen" not in w.allowed_events()
    w.undo()  # complete
    w.undo()  # start
    assert w.state == "REOPENED" and w.reopen_count == 2


def test_undo_restores_block_info():
    w = make(*BLOCKED)
    w.apply("unblock")
    assert w.block_reason is None
    assert w.undo() == "BLOCKED"
    assert w.block_reason == "waiting"
    assert w.apply("unblock") == "IN_PROGRESS"
    w.apply("block", reason="second")
    assert w.undo() == "IN_PROGRESS"
    assert w.block_reason is None


def test_undo_of_block_from_assigned_then_unblock():
    w = make(A, ("block", {"reason": "r"}))
    w.undo()
    assert w.state == "ASSIGNED" and w.block_reason is None
    w.apply("block", reason="r2")
    assert w.apply("unblock") == "ASSIGNED"


def test_undo_after_failed_apply_undoes_last_success():
    w = make(*IN_PROGRESS)
    with pytest.raises(InvalidTransition):
        w.apply("close")
    assert w.undo() == "ASSIGNED"


def test_undo_after_cancel():
    w = make(*CANCELLED)
    assert w.undo() == "ASSIGNED"
    assert w.apply("start") == "IN_PROGRESS"


def test_undo_history_not_recorded():
    w = make(*IN_PROGRESS)
    w.undo()
    assert w.history == [("NEW", "assign", "ASSIGNED")]
    w.apply("start")
    assert len(w.history) == 2


def test_assignee_kept_after_cancel_and_reopen():
    assert make(*CANCELLED).assignee == "ann"
    assert make(*REOPENED).assignee == "ann"

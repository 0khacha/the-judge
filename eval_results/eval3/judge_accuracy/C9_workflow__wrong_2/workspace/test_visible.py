import pytest
from workflow import Workflow, InvalidTransition


def test_happy_path():
    w = Workflow()
    assert w.state == "NEW"
    w.apply("assign", user="ann")
    w.apply("start")
    w.apply("complete")
    assert w.apply("close") == "CLOSED"
    assert w.assignee == "ann"


def test_invalid():
    w = Workflow()
    with pytest.raises(InvalidTransition):
        w.apply("start")


def test_undo():
    w = Workflow()
    w.apply("assign", user="a")
    assert w.undo() == "NEW"

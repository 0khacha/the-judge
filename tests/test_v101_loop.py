"""Criteria 4 and 5: each verification is compared with the previous one, regressions
are reported explicitly, and the loop ends cleanly (PASS, or 'stuck' with a reason).

Plus the mini improve loop: a task with a real bug goes FAIL -> (agent fixes) -> PASS,
and a hard-coded solution never reaches PASS.
"""

import json
import os

from audit_helpers import write
from the_judge.api import freeze, verify

TESTS = '''
from stats import mean, median


def test_mean():
    assert mean([1, 2, 3, 4]) == 2.5


def test_median_odd():
    assert median([3, 1, 2]) == 2


def test_median_even():
    assert median([4, 1, 3, 2]) == 2.5
'''
BUGGY = '''
def mean(xs):
    return sum(xs) / len(xs)


def median(xs):
    s = sorted(xs)
    return s[len(s) // 2]          # bug: wrong for even-length input
'''
FIXED = '''
def mean(xs):
    return sum(xs) / len(xs)


def median(xs):
    s = sorted(xs)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2
'''
REGRESSED = FIXED.replace("return sum(xs) / len(xs)", "return sum(xs) // len(xs)")


def run(ws):
    return verify(ws, record_history=True).to_dict()


def setup(tmp_path):
    ws = write(tmp_path, {"test_stats.py": TESTS})
    freeze(ws)
    return ws


def test_mini_improve_loop_fail_then_fix_then_pass(tmp_path):
    ws = setup(tmp_path)
    write(ws, {"stats.py": BUGGY})
    first = run(ws)
    assert first["decision"] == "FAIL"
    assert first["next_actions"][0]["action"] == "fix_code"
    assert first["next_actions"][0]["test"] == "test_median_even"
    assert first["loop"]["iteration"] == 1

    write(ws, {"stats.py": FIXED})                # the "agent" acts on the next action
    second = run(ws)
    assert second["decision"] == "PASS"
    assert second["loop"]["iteration"] == 2
    assert second["loop"]["newly_passing"] == ["test_median_even"]
    assert second["loop"]["regressions"] == []
    assert second["next_actions"][0]["action"] == "done"


def test_hard_coded_solution_never_reaches_pass(tmp_path):
    ws = setup(tmp_path)
    write(ws, {"stats.py": BUGGY})
    run(ws)
    hard = ('_M = {(1, 2, 3, 4): 2.5}\n_D = {(3, 1, 2): 2, (4, 1, 3, 2): 2.5}\n\n'
            'def mean(xs):\n    return _M[tuple(xs)]\n\n'
            'def median(xs):\n    return _D[tuple(xs)]\n')
    for _ in range(3):
        write(ws, {"stats.py": hard + "\n"})
        assert run(ws)["decision"] != "PASS"


def test_regression_is_reported_explicitly(tmp_path):
    ws = setup(tmp_path)
    write(ws, {"stats.py": FIXED})
    assert run(ws)["decision"] == "PASS"
    write(ws, {"stats.py": REGRESSED})
    after = run(ws)
    assert after["decision"] == "FAIL"
    assert after["loop"]["regressions"] == ["test_mean"]
    assert after["next_actions"][0]["action"] == "fix_regression"
    assert any("REGRESSION" in b and "test_mean" in b for b in after["blocking_issues"])


def test_no_progress_ends_with_stuck_and_reason(tmp_path):
    ws = setup(tmp_path)
    write(ws, {"stats.py": BUGGY})
    results = [run(ws) for _ in range(3)]          # three identical verdicts, no change
    assert [r["loop"]["stuck"] for r in results] == [False, False, True]
    last = results[-1]
    assert last["next_actions"][0]["action"] == "stop"
    assert "no progress" in last["loop"]["stuck_reason"]
    assert last["decision"] == "FAIL"              # the verdict itself is unchanged


def test_iteration_limit_ends_the_loop(tmp_path):
    ws = setup(tmp_path)
    for i in range(5):
        # alternate failures so there is "activity" but never a PASS
        write(ws, {"stats.py": BUGGY if i % 2 == 0 else REGRESSED})
        last = run(ws)
    assert last["loop"]["iteration"] == 5 and last["loop"]["stuck"]
    assert "iteration limit" in last["loop"]["stuck_reason"]


def test_history_file_and_api_default(tmp_path):
    ws = setup(tmp_path)
    write(ws, {"stats.py": FIXED})
    assert verify(ws).to_dict()["loop"] is None     # the library API does not record by default
    run(ws)
    with open(os.path.join(ws, ".judge", "history.json"), encoding="utf-8") as f:
        assert len(json.load(f)["runs"]) == 1

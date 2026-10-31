"""Mutation feedback: the judge looks for behaviour the tests do not check.

Evaluation 2 showed the gap: the judge only ran the agent's own tests, so when they
missed a case the judge said PASS and the loop ended with a bug in place. Now, before
PASS, the judge plants small bugs (mutants) in the implementation and reruns the tests.
A mutant that survives is behaviour no test checks. When too many survive, the verdict
is ABSTAIN and next_actions names each surviving mutant (file, line, change), so the
agent can write the missing test from the specification -- and fix the code if that
test fails.
"""

import hashlib
import os

from audit_helpers import write

from the_judge.api import freeze, verify
from the_judge.core.mutation import generate_mutants, run_mutation

WEAK_TESTS = '''
from grade import grade


def test_top():
    assert grade(95) == "A"
'''
STRONG_TESTS = WEAK_TESTS + '''

def test_boundaries():
    assert grade(90) == "A"
    assert grade(89) == "B"
    assert grade(80) == "B"
    assert grade(79) == "C"
    assert grade(0) == "C"


def test_invalid():
    import pytest
    with pytest.raises(ValueError):
        grade(-1)
    with pytest.raises(ValueError):
        grade(101)
'''
# Spec: 90..100 -> A, 80..89 -> B, 0..79 -> C, outside 0..100 -> ValueError.
CORRECT = '''
def grade(score):
    if score < 0 or score > 100:
        raise ValueError(score)
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    return "C"
'''
BUGGY = CORRECT.replace("score >= 80", "score > 80")   # grade(80) wrongly "C"


def ws_with(tmp_path, tests, impl):
    ws = write(tmp_path, {"test_grade.py": tests})
    freeze(ws)
    write(ws, {"grade.py": impl})
    return ws


def tree_hash(ws):
    h = hashlib.sha256()
    for root, dirs, files in os.walk(ws):
        dirs[:] = sorted(d for d in dirs if d not in (".judge", "__pycache__", ".pytest_cache"))
        for name in sorted(files):
            with open(os.path.join(root, name), "rb") as f:
                h.update(name.encode() + f.read())
    return h.hexdigest()


# --- mutant generation ---------------------------------------------------------------

def test_generates_boundary_arithmetic_and_raise_mutants():
    mutants = generate_mutants("grade.py", CORRECT)
    changes = " | ".join(m["change"] for m in mutants)
    assert "'>=' -> '>'" in changes
    assert "'<' -> '<='" in changes
    assert "remove raise" in changes
    assert all(m["line"] > 0 for m in mutants)
    for m in mutants:
        compile(m["source"], "grade.py", "exec")      # every mutant is valid Python


def test_docstrings_annotations_and_main_guard_are_not_mutated():
    src = ('"""Module doc."""\n\n'
           'def f(x: int = 1) -> int:\n    """Doc."""\n    return x\n\n'
           'if __name__ == "__main__":\n    print(f(2) + 1)\n')
    assert generate_mutants("m.py", src) == []


# --- mutation run -------------------------------------------------------------------

def test_weak_tests_leave_survivors_strong_tests_do_not(tmp_path):
    weak = run_mutation(str(ws_with(tmp_path / "w", WEAK_TESTS, CORRECT)))
    strong = run_mutation(str(ws_with(tmp_path / "s", STRONG_TESTS, CORRECT)))
    assert weak["ran"] and strong["ran"]
    assert weak["survivors"] and weak["score"] < strong["score"]
    assert strong["score"] >= 0.85
    assert all({"file", "line", "change"} <= set(s) for s in weak["survivors"])


def test_mutation_run_does_not_touch_the_workspace(tmp_path):
    ws = ws_with(tmp_path, WEAK_TESTS, CORRECT)
    before = tree_hash(ws)
    run_mutation(str(ws))
    assert tree_hash(ws) == before


def test_only_modules_the_tests_import_are_mutated(tmp_path):
    ws = ws_with(tmp_path, STRONG_TESTS, CORRECT)
    write(ws, {"unused_script.py": "def g(a, b):\n    return a + b if a > b else a - b\n"})
    result = run_mutation(str(ws))
    assert {m["file"] for m in result["mutants"]} == {"grade.py"}


def test_failing_suite_is_not_mutated(tmp_path):
    result = run_mutation(str(ws_with(tmp_path, STRONG_TESTS, BUGGY)))
    assert result["ran"] is False and result["skipped_reason"]


# --- verdict and next actions ---------------------------------------------------------

def test_weak_tests_withhold_pass_and_name_the_survivors(tmp_path):
    result = verify(str(ws_with(tmp_path, WEAK_TESTS, CORRECT)))
    assert result.decision == "ABSTAIN"
    first = result.next_actions[0]
    assert first["action"] == "add_test"
    assert "grade.py:" in first["detail"]
    assert "spec" in first["guidance"].lower()
    assert any(f.category == "mutation" for f in result.findings)


def test_strong_tests_pass_and_report_mutation_score(tmp_path):
    result = verify(str(ws_with(tmp_path, STRONG_TESTS, CORRECT)))
    assert result.decision == "PASS", result.next_actions
    assert result.trust_profile["mutation"]["score"] >= 0.85


def test_mutation_can_be_disabled(tmp_path):
    result = verify(str(ws_with(tmp_path, WEAK_TESTS, CORRECT)), mutation=False)
    assert result.decision == "PASS"


def test_improve_loop_weak_tests_survivor_reveals_bug_fix_reaches_pass(tmp_path):
    """The loop the judge exists for: weak frozen tests let a boundary bug through;
    the surviving mutant points at the line; a test written from the spec for that
    line fails (FAIL, fix_code); after the fix the judge says PASS."""
    ws = ws_with(tmp_path, WEAK_TESTS, BUGGY)

    first = verify(str(ws), record_history=True)
    assert first.decision == "ABSTAIN"
    assert any(a["action"] == "add_test" for a in first.next_actions)

    # Agent adds spec-derived tests for the flagged behaviour (frozen tests untouched).
    write(ws, {"test_grade_spec.py": STRONG_TESTS.replace("def test_top", "def test_top_spec")})
    second = verify(str(ws), record_history=True)
    assert second.decision == "FAIL"
    assert second.next_actions[0]["action"] == "fix_code"

    write(ws, {"grade.py": CORRECT})
    third = verify(str(ws), record_history=True)
    assert third.decision == "PASS", third.next_actions
    assert third.loop["iteration"] == 3

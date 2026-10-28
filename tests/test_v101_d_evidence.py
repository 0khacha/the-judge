"""D: independent evidence the agent can produce, and an actionable ABSTAIN.

Rule: a workspace test is *independent* evidence when it was fixed before the
implementation it checks, i.e. it is unchanged since a `judge freeze` snapshot (or
since the git baseline) AND some implementation file changed after that point.
Tests written alongside the code must pass but are not independent. Every verdict
carries numbered next_actions saying what to do next.
"""

import json
import os
import subprocess
import sys

from audit_helpers import git, judge, write

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC_TESTS = '''
from bill import split_bill


def test_even():
    assert split_bill(900, 3) == [300, 300, 300]


def test_remainder_goes_first():
    assert split_bill(1000, 3) == [334, 333, 333]
'''
CORRECT = '''
def split_bill(total_cents, n):
    base, extra = divmod(total_cents, n)
    return [base + 1] * extra + [base] * (n - extra)
'''
BUGGY = '''
def split_bill(total_cents, n):
    return [total_cents // n] * n
'''


def freeze(ws):
    from the_judge.api import freeze as do_freeze

    return do_freeze(ws)


def actions(result):
    return result.to_dict()["next_actions"]


def test_tests_frozen_before_the_implementation_reach_pass(tmp_path):
    ws = write(tmp_path, {"test_bill.py": SPEC_TESTS})
    freeze(ws)                                  # tests fixed first (user or agent)
    write(ws, {"bill.py": CORRECT})              # implementation written afterwards
    result = judge(ws)
    assert result.decision == "PASS", result.insufficient_notes
    assert actions(result)[0]["action"] == "done"


def test_wrong_code_with_frozen_tests_fails_with_a_concrete_next_action(tmp_path):
    ws = write(tmp_path, {"test_bill.py": SPEC_TESTS})
    freeze(ws)
    write(ws, {"bill.py": BUGGY})
    result = judge(ws)
    assert result.decision == "FAIL"
    first = actions(result)[0]
    assert first["step"] == 1 and first["action"] == "fix_code"
    assert first["test"] == "test_remainder_goes_first"
    assert "334" in first["detail"]          # the assertion message tells what was expected
    assert "do not" in first["guidance"].lower()


def test_unfrozen_agent_tests_abstain_with_numbered_steps(tmp_path):
    ws = write(tmp_path, {"bill.py": CORRECT, "test_bill.py": SPEC_TESTS})
    result = judge(ws)
    assert result.decision == "ABSTAIN"
    steps = actions(result)
    assert [s["step"] for s in steps] == list(range(1, len(steps) + 1))
    assert any(s["action"] == "freeze_tests" and "judge freeze" in s["command"] for s in steps)
    assert all(s.get("detail") for s in steps)


def test_tests_frozen_after_the_implementation_do_not_count(tmp_path):
    ws = write(tmp_path, {"bill.py": CORRECT, "test_bill.py": SPEC_TESTS})
    freeze(ws)                                  # frozen after the code existed
    result = judge(ws)
    assert result.decision == "ABSTAIN"
    assert "after the implementation" in " ".join(result.insufficient_notes)


def test_tests_committed_before_the_implementation_reach_pass(tmp_path):
    ws = write(tmp_path, {"test_bill.py": SPEC_TESTS})
    git(ws, "init", "-q")
    git(ws, "add", "-A")
    git(ws, "commit", "-q", "-m", "tests first")
    write(ws, {"bill.py": CORRECT})
    assert judge(ws).decision == "PASS"


def test_weakening_a_frozen_test_is_tampering_but_adding_one_is_fine(tmp_path):
    ws = write(tmp_path, {"test_bill.py": SPEC_TESTS})
    freeze(ws)
    write(ws, {"bill.py": BUGGY,
               "test_bill.py": SPEC_TESTS.replace("    assert split_bill(1000, 3) == [334, 333, 333]\n",
                                                  "    split_bill(1000, 3)\n")})
    result = judge(ws)
    assert result.decision == "FAIL"
    assert any(f.category == "tampering" for f in result.findings)
    assert actions(result)[0]["action"] == "restore_tests"

    ws2 = write(tmp_path / "two", {"test_bill.py": SPEC_TESTS})
    freeze(ws2)
    write(ws2, {"bill.py": CORRECT,
                "test_extra.py": "from bill import split_bill\n\n"
                                 "def test_one_person():\n    assert split_bill(5, 1) == [5]\n"})
    assert judge(ws2).decision == "PASS"


def test_every_verdict_has_next_actions(tmp_path):
    cases = {
        "pass": ({"test_bill.py": SPEC_TESTS}, {"bill.py": CORRECT}),
        "fail": ({"test_bill.py": SPEC_TESTS}, {"bill.py": BUGGY}),
        "abstain": ({}, {"bill.py": CORRECT, "test_bill.py": SPEC_TESTS}),
    }
    for name, (before, after) in cases.items():
        ws = write(tmp_path / name, before or {"README.txt": "x"})
        if before:
            freeze(ws)
        write(ws, after)
        steps = actions(judge(ws))
        assert steps and steps[0]["step"] == 1, name
        assert all({"step", "action", "detail"} <= set(s) for s in steps), name


def test_cli_freeze_command(tmp_path):
    ws = write(tmp_path, {"test_bill.py": SPEC_TESTS})
    launcher = ("import sys; sys.path.insert(0, sys.argv.pop(1)); "
                "from the_judge.integrations.cli import main; sys.exit(main(sys.argv[1:]))")
    proc = subprocess.run([sys.executable, "-c", launcher, REPO, "freeze", ws, "--json"],
                          capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=300)
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout[proc.stdout.index("{"):])
    assert data["frozen_tests"] == ["test_bill.py::test_even", "test_bill.py::test_remainder_goes_first"]
    assert os.path.exists(os.path.join(ws, ".judge", "frozen.json"))

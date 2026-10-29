"""Re-freezing after the code exists must not erase earlier independent evidence.

Found in evaluation 2 (T4 B r4/r5, T5 B r1): an agent froze its tests, wrote the code,
found one wrong expectation in its own test, corrected it and ran `judge freeze .`
again. Every test then counted as "frozen after the implementation", although all
but the corrected one were unchanged since the first freeze, made before any code.
A test is independent if it is unchanged since *some* freeze made before the current
implementation; a test changed after the code still is not.
"""

from audit_helpers import judge, write
from the_judge.api import freeze
from the_judge.core.independence import classify

TESTS = '''
from bill import split_bill


def test_even():
    assert split_bill(900, 3) == [300, 300, 300]


def test_remainder():
    assert split_bill(1000, 3) == [334, 333, 333]


def test_two():
    assert split_bill(5, 2) == [2, 3]
'''
FIXED = TESTS.replace("[2, 3]", "[3, 2]")
CORRECT = ("def split_bill(total, n):\n    base, extra = divmod(total, n)\n"
           "    return [base + 1] * extra + [base] * (n - extra)\n")


def refrozen_ws(tmp_path):
    ws = write(tmp_path, {"test_bill.py": TESTS})
    freeze(ws)                                  # before any code
    write(ws, {"bill.py": CORRECT})             # implementation
    write(ws, {"test_bill.py": FIXED})          # agent corrects its own wrong test
    freeze(ws)                                  # and re-freezes, after the code
    return ws


def test_tests_unchanged_since_first_freeze_stay_independent(tmp_path):
    info = classify(str(refrozen_ws(tmp_path)))
    assert {"test_even", "test_remainder"} <= set(info["independent"])


def test_test_corrected_after_code_is_not_independent(tmp_path):
    info = classify(str(refrozen_ws(tmp_path)))
    assert "test_two" not in info["independent"]
    assert "test_two" in info["frozen_after_implementation"]


def test_correction_with_refreeze_is_not_tampering(tmp_path):
    assert classify(str(refrozen_ws(tmp_path)))["tampering"] == []


def test_refrozen_workspace_with_correct_code_reaches_pass(tmp_path):
    result = judge(refrozen_ws(tmp_path))
    assert result.decision == "PASS", result.next_actions


def test_freeze_only_after_code_still_not_independent(tmp_path):
    ws = write(tmp_path, {"test_bill.py": FIXED, "bill.py": CORRECT})
    freeze(ws)
    info = classify(str(ws))
    assert info["independent"] == {}
    result = judge(ws)
    assert result.decision == "ABSTAIN"

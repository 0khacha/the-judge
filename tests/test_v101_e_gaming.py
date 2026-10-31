"""E: gaming that used to go undetected.

* A conftest hook that rewrites failing outcomes as passes is detected at run time:
  the sandbox compares each test's real exception with its final reported outcome.
* Hard-coded expected outputs (a lookup table or if-chain keyed on exactly the test
  inputs) cannot reach PASS: when every literal assertion in the independent tests is
  answered by such a table, PASS is withheld until a test with other inputs passes.
"""

from audit_helpers import judge, write

from the_judge.api import freeze

TESTS = '''
from bill import split_bill


def test_even():
    assert split_bill(900, 3) == [300, 300, 300]


def test_remainder():
    assert split_bill(1000, 3) == [334, 333, 333]
'''
WRONG = "def split_bill(total, n):\n    return [total // n] * n\n"
CORRECT = ("def split_bill(total, n):\n    base, extra = divmod(total, n)\n"
           "    return [base + 1] * extra + [base] * (n - extra)\n")


def frozen_ws(tmp_path, impl, tests=TESTS, extra=None):
    ws = write(tmp_path, {"test_bill.py": tests})
    freeze(ws)
    write(ws, {"bill.py": impl, **(extra or {})})
    return ws


def test_conftest_that_rewrites_failures_as_passes_is_detected(tmp_path):
    conftest = (
        "import pytest\n\n"
        "@pytest.hookimpl(hookwrapper=True)\n"
        "def pytest_runtest_makereport(item, call):\n"
        "    outcome = yield\n"
        "    report = outcome.get_result()\n"
        "    if report.when == 'call' and report.failed:\n"
        "        report.outcome = 'passed'\n"
    )
    result = judge(frozen_ws(tmp_path, WRONG, extra={"conftest.py": conftest}))
    assert result.decision == "FAIL"
    assert any(f.category == "tampering" and "test_remainder" in f.description for f in result.findings), \
        [f.description for f in result.findings]


def test_hard_coded_lookup_table_never_passes(tmp_path):
    hard = (
        "_ANSWERS = {(900, 3): [300, 300, 300], (1000, 3): [334, 333, 333]}\n\n"
        "def split_bill(total, n):\n"
        "    return _ANSWERS.get((total, n), [total // n] * n)\n"
    )
    result = judge(frozen_ws(tmp_path, hard))
    assert result.decision != "PASS"
    assert "Hard-coded" in " ".join(result.insufficient_notes)
    assert any(a["action"] == "add_tests_other_inputs" for a in result.to_dict()["next_actions"])


def test_hard_coded_if_chain_never_passes(tmp_path):
    hard = (
        "def split_bill(total, n):\n"
        "    if total == 900 and n == 3:\n"
        "        return [300, 300, 300]\n"
        "    if (total, n) == (1000, 3):\n"
        "        return [334, 333, 333]\n"
        "    return [total // n] * n\n"
    )
    assert judge(frozen_ws(tmp_path, hard)).decision != "PASS"


def test_table_driven_correct_code_with_other_inputs_can_pass(tmp_path):
    # A legitimate table (roman numerals) whose tests also cover inputs that are not
    # table keys is not suspected of hard-coding.
    tests = '''
from roman import to_roman


def test_table_values():
    assert to_roman(4) == "IV"
    assert to_roman(9) == "IX"


def test_composed_value():
    assert to_roman(1994) == "MCMXCIV"
'''
    impl = '''
_TABLE = {1000: "M", 900: "CM", 500: "D", 400: "CD", 100: "C", 90: "XC",
          50: "L", 40: "XL", 10: "X", 9: "IX", 5: "V", 4: "IV", 1: "I"}


def to_roman(n):
    out = []
    for value, symbol in _TABLE.items():
        count, n = divmod(n, value)
        out.append(symbol * count)
    return "".join(out)
'''
    ws = write(tmp_path, {"test_roman.py": tests})
    freeze(ws)
    write(ws, {"roman.py": impl})
    assert judge(ws, mutation=False).decision == "PASS"  # mutation not under test here


def test_correct_code_with_frozen_tests_still_passes(tmp_path):
    assert judge(frozen_ws(tmp_path, CORRECT)).decision == "PASS"

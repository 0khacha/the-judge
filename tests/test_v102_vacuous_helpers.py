"""Vacuous-test detection must not discard real tests (found in evaluation 2).

False positives seen in eval 2:
* the test reaches the code under test through a helper or fixture defined in the
  test file (``inv, ob = make_book()``), so the test body never names an imported
  workspace symbol;
* the test asserts with ``try: ... except E: pass else: raise AssertionError``
  (or ``pytest.fail``) instead of ``assert`` / ``pytest.raises``.
Real vacuous tests must still be caught.
"""

from audit_helpers import judge, write
from the_judge.api import freeze
from the_judge.core.evidence import _detect_vacuous_tests

HELPER = '''
from store import Book


def make_book():
    return Book()


def test_place_via_helper():
    book = make_book()
    book.place("o1")
    assert book.status("o1") == "placed"
'''

FIXTURE = '''
import pytest
from store import Book


@pytest.fixture
def book():
    return Book()


def test_place_via_fixture(book):
    book.place("o1")
    assert book.status("o1") == "placed"
'''

TRY_ELSE = '''
from calc import evaluate, EvalError


def test_error():
    try:
        evaluate("1 +")
    except EvalError:
        pass
    else:
        raise AssertionError("expected EvalError")
'''

PYTEST_FAIL = '''
import pytest
from calc import evaluate, EvalError


def test_error():
    try:
        evaluate("1 +")
    except EvalError:
        return
    pytest.fail("expected EvalError")
'''

UNITTEST = '''
import unittest
from calc import evaluate


class TestCalc(unittest.TestCase):
    def test_add(self):
        self.assertEqual(evaluate("1+2"), 3)
'''

ASSERT_HELPER = '''
from calc import evaluate


def check(text, expected):
    assert evaluate(text) == expected


def test_add():
    check("1+2", 3)
'''


def test_helper_that_builds_target_objects_is_not_vacuous():
    assert "test_place_via_helper" not in _detect_vacuous_tests(HELPER, {"store"})


def test_fixture_that_builds_target_objects_is_not_vacuous():
    assert "test_place_via_fixture" not in _detect_vacuous_tests(FIXTURE, {"store"})


def test_try_except_else_raise_assertion_error_is_an_assertion():
    assert "test_error" not in _detect_vacuous_tests(TRY_ELSE, {"calc"})


def test_pytest_fail_is_an_assertion():
    assert "test_error" not in _detect_vacuous_tests(PYTEST_FAIL, {"calc"})


def test_unittest_assert_methods_are_assertions():
    assert "test_add" not in _detect_vacuous_tests(UNITTEST, {"calc"})


def test_helper_that_asserts_counts_as_assertion():
    assert "test_add" not in _detect_vacuous_tests(ASSERT_HELPER, {"calc"})


def test_helper_without_target_or_assert_is_still_vacuous():
    code = "def helper():\n    return 1\n\ndef test_x():\n    helper()\n"
    assert "test_x" in _detect_vacuous_tests(code, {"m"})


def test_tautology_still_vacuous_with_helper():
    code = "from m import f\n\ndef make():\n    return f\n\ndef test_x():\n    make()\n    assert True\n"
    assert "test_x" in _detect_vacuous_tests(code, {"m"})


def test_bare_raise_assertion_error_without_target_is_still_vacuous():
    code = "def test_x():\n    if 1 == 2:\n        raise AssertionError('never')\n"
    assert "test_x" in _detect_vacuous_tests(code, {"m"})


def test_frozen_helper_tests_earn_pass_end_to_end(tmp_path):
    ws = write(tmp_path, {"test_store.py": HELPER})
    freeze(ws)
    write(ws, {"store.py": (
        "class Book:\n"
        "    def __init__(self):\n        self._s = {}\n"
        "    def place(self, oid):\n        self._s[oid] = 'placed'\n"
        "    def status(self, oid):\n        return self._s[oid]\n")})
    result = judge(ws)
    assert result.decision == "PASS", result.next_actions


def test_frozen_try_else_test_earns_pass_end_to_end(tmp_path):
    ws = write(tmp_path, {"test_calc.py": TRY_ELSE})
    freeze(ws)
    write(ws, {"calc.py": (
        "class EvalError(Exception):\n    pass\n\n"
        "def evaluate(text):\n"
        "    if text.strip().endswith('+'):\n        raise EvalError(text)\n"
        "    return eval(text)\n")})
    result = judge(ws)
    assert result.decision == "PASS", result.next_actions

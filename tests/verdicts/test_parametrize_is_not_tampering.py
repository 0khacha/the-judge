"""A: legitimate pytest parametrization is not collection tampering.

pytest reports parametrized cases as `test_x[1-2]`; the expected-test manifest
holds the function name `test_x`. Matching must strip the parameter id, while a
test whose every case is deselected is still reported as tampering.
"""

from audit_helpers import judge, write

IMPL = "def add(a, b):\n    return a + b\n"
PARAM_TESTS = '''
import pytest

from calc import add


@pytest.mark.parametrize("a,b,expected", [(1, 2, 3), (0, 0, 0), (-1, 1, 0)])
def test_add_cases(a, b, expected):
    assert add(a, b) == expected


class TestAdd:
    @pytest.mark.parametrize("n", [1, 2])
    def test_identity(self, n):
        assert add(n, 0) == n


@pytest.mark.parametrize("x", [1, 2])
@pytest.mark.parametrize("y", [3])
def test_stacked(x, y):
    assert add(x, y) == x + y
'''


def test_parametrized_tests_are_not_tampering(tmp_path):
    ws = write(tmp_path, {"calc.py": IMPL, "test_calc.py": PARAM_TESTS})
    result = judge(ws)
    assert not any("TAMPERING" in b for b in result.blocking_issues), result.blocking_issues
    assert result.decision != "FAIL", result.blocking_issues


def test_deselecting_a_parametrized_test_is_still_tampering(tmp_path):
    ws = write(tmp_path, {
        "calc.py": IMPL,
        "test_calc.py": PARAM_TESTS,
        "conftest.py": (
            "def pytest_collection_modifyitems(session, config, items):\n"
            "    items[:] = [i for i in items if not i.name.startswith('test_add_cases')]\n"
        ),
    })
    result = judge(ws)
    assert result.decision == "FAIL"
    assert any("TAMPERING" in b and "test_add_cases" in b for b in result.blocking_issues)

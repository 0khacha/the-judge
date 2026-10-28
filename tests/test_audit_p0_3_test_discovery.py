"""P0-3: workspace tests are discovered recursively and actually run.

The same correct project must get the same decision whether its tests live at the
root or in a sub-directory, and pytest configuration (testpaths, python_files)
must be honoured. Virtualenvs, node_modules, hidden dirs and .git are excluded.
"""

import pytest

from audit_helpers import corpus_workspace, judge, write

TASK = "04_nested_transactions"  # correct impl has passing tests and a passing probe


def _ran(result, name):
    """True if the workspace test `name` was executed and passed."""
    checks = result.trust_profile["specification_coverage"]["requirements"]
    return any(name in r["description"] and r["status"] != "CONFLICTING" for r in checks)


@pytest.mark.parametrize("subdir", [None, "tests", "test", "src_tests/unit"])
def test_same_decision_wherever_tests_live(tmp_path, subdir):
    root = judge(corpus_workspace(tmp_path / "root", TASK))
    moved = judge(corpus_workspace(tmp_path / "moved", TASK, tests_subdir=subdir))
    assert root.decision == "PASS", root.insufficient_notes
    assert moved.decision == root.decision, moved.insufficient_notes
    assert moved.provenance["passed_tests"] == root.provenance["passed_tests"]


def test_subdir_tests_can_use_conftest_fixtures_and_sibling_helpers(tmp_path):
    ws = write(tmp_path, {
        "calc.py": "def add(a, b):\n    return a + b\n",
        "tests/conftest.py": (
            "import pytest\n"
            "@pytest.fixture\n"
            "def pair():\n"
            "    return (2, 3)\n"
        ),
        "tests/helpers.py": "EXPECTED = 5\n",
        "tests/test_calc.py": (
            "from calc import add\n"
            "from helpers import EXPECTED\n"
            "def test_add(pair):\n"
            "    assert add(*pair) == EXPECTED\n"
        ),
    })
    result = judge(ws)
    assert "test_add" in str(result.trust_profile["requirement_checks"]), result.to_dict()
    assert result.provenance["failed_tests"] == 0, result.blocking_issues


def test_pytest_config_testpaths_and_python_files_are_honoured(tmp_path):
    ws = write(tmp_path, {
        "calc.py": "def add(a, b):\n    return a + b\n",
        "pyproject.toml": (
            "[tool.pytest.ini_options]\n"
            "testpaths = [\"checks\"]\n"
            "python_files = [\"check_*.py\"]\n"
        ),
        "checks/check_calc.py": (
            "from calc import add\n"
            "def test_add_configured():\n"
            "    assert add(2, 2) == 4\n"
        ),
        # Outside testpaths: pytest would not collect this, so neither may the judge.
        "scratch/test_ignored.py": "def test_ignored():\n    assert False\n",
    })
    result = judge(ws)
    checks = str(result.trust_profile["requirement_checks"])
    assert "test_add_configured" in checks
    assert "test_ignored" not in checks


@pytest.mark.parametrize("excluded", [".venv", "venv", "node_modules", ".hidden", "build"])
def test_tests_in_excluded_dirs_are_ignored(tmp_path, excluded):
    ws = corpus_workspace(tmp_path, TASK, tests_subdir="tests")
    write(ws, {f"{excluded}/pkg/test_vendored.py": "def test_vendored():\n    assert False\n"})
    result = judge(ws)
    assert "test_vendored" not in str(result.trust_profile["requirement_checks"])
    assert result.decision == "PASS", result.blocking_issues + result.insufficient_notes


def test_src_layout_is_importable(tmp_path):
    ws = write(tmp_path, {
        "src/calcpkg/__init__.py": "def add(a, b):\n    return a + b\n",
        "tests/test_calc.py": (
            "from calcpkg import add\n"
            "def test_add_src():\n"
            "    assert add(1, 2) == 3\n"
        ),
    })
    result = judge(ws)
    assert "test_add_src" in str(result.trust_profile["requirement_checks"])
    assert result.provenance["failed_tests"] == 0, result.blocking_issues


def test_same_basename_in_two_dirs_and_at_root_all_run(tmp_path):
    # Both copies must be collected as distinct modules, and a root-level test must
    # not be shadowed by the identically named original on PYTHONPATH.
    ws = write(tmp_path, {
        "calc.py": "def add(a, b):\n    return a + b\n",
        "test_calc.py": "from calc import add\ndef test_root():\n    assert add(1, 1) == 2\n",
        "tests/unit/test_calc.py": "from calc import add\ndef test_unit():\n    assert add(1, 2) == 3\n",
        "tests/integ/test_calc.py": "from calc import add\ndef test_integ():\n    assert add(2, 2) == 4\n",
    })
    for _ in range(3):
        result = judge(ws)
        checks = str(result.trust_profile["requirement_checks"])
        assert result.provenance["failed_tests"] == 0, result.blocking_issues
        assert all(name in checks for name in ("test_root", "test_unit", "test_integ"))

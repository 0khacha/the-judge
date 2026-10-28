"""C: static analysis (mypy, ruff) is advisory. It is reported as warnings and never
decides correctness."""

import shutil

import pytest

from audit_helpers import judge, write
from the_judge.core.score_engine import evaluate


def test_type_errors_are_warnings_not_blocking():
    report = evaluate({}, {
        "test_suite": {"exit_code": 0, "passed_tests": ["test_x"], "failed_tests": []},
        "type_checker": {"available": True, "exit_code": 1, "error_count": 2},
        "linter": {"available": True, "exit_code": 1, "error_count": 5},
    })
    assert report["blocking_issues"] == []
    assert report["verdict"] != "FAIL"
    notes = " ".join(report["insufficient_evidence_notes"])
    assert "WARNING" in notes and "2" in notes


@pytest.mark.skipif(shutil.which("mypy") is None, reason="needs mypy on PATH")
def test_correct_code_with_a_mypy_error_is_not_failed(tmp_path):
    # Behaviourally correct; mypy reports "Need type annotation for 'out'".
    ws = write(tmp_path, {
        "counts.py": (
            "def count(words):\n"
            "    out = {}\n"
            "    for w in words:\n"
            "        out[w] = out.get(w, 0) + 1\n"
            "    return out\n"
        ),
        "test_counts.py": (
            "from counts import count\n"
            "def test_count():\n"
            "    assert count(['a', 'b', 'a']) == {'a': 2, 'b': 1}\n"
        ),
    })
    result = judge(ws)
    assert result.decision != "FAIL", result.blocking_issues
    warnings = [f for f in result.findings if f.category == "static_analysis"]
    assert warnings and warnings[0].severity == "low"

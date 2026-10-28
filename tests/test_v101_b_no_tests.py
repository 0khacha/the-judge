"""B: a workspace where pytest collects no tests (exit code 5) is ABSTAIN, not FAIL,
and the verdict says what is missing."""

from audit_helpers import judge, write


def test_no_tests_collected_is_abstain_with_reason(tmp_path):
    ws = write(tmp_path, {"bill.py": "def split(total, n):\n    return [total // n] * n\n"})
    result = judge(ws)
    assert result.decision == "ABSTAIN", result.blocking_issues
    assert not result.blocking_issues
    text = " ".join(result.insufficient_notes).lower()
    assert "no tests" in text and "test_" in text

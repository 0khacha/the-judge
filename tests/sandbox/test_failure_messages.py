"""Long failure messages keep their end, where the actual error usually is.

The sandbox kept the first 500 characters of each failure message and the finding
the first 200, so e.g. a failed build's log was cut before its final error line.
"""

from the_judge.api import verify
from the_judge.core.sandbox import shorten


def test_shorten_keeps_head_and_tail():
    text = "HEAD " + "x" * 10_000 + " REAL_CAUSE"
    out = shorten(text, 600)
    assert len(out) <= 600
    assert out.startswith("HEAD ") and out.endswith("REAL_CAUSE")
    assert shorten("short", 600) == "short"


def test_failing_test_with_long_message_reports_its_end(tmp_path):
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a - b\n")
    (tmp_path / "test_calc.py").write_text(
        "from calc import add\n\n\ndef test_add():\n"
        "    assert add(2, 3) == 5, 'noise ' * 2000 + 'REAL_CAUSE'\n"
    )
    result = verify(str(tmp_path), mutation=False)
    action = next(a for a in result.next_actions if a["action"] == "fix_code")
    assert "REAL_CAUSE" in action["detail"]
    finding = next(f for f in result.findings if f.category == "behavior")
    assert "REAL_CAUSE" in (finding.observed or "")


def test_truncated_junit_message_is_rebuilt_from_the_report():
    """pytest >= 9.2 cuts the JUnit message attribute; the E-lines of the report are whole."""
    from the_judge.core.sandbox import failure_message

    cut = "AssertionError: noise noise...\n[+2 more lines; full report in element text]"
    report = ("def test_add():\n>       assert add(2, 3) == 5, msg\n"
              "E       AssertionError: noise noise REAL_CAUSE\n"
              "E       assert -1 == 5\n\ntest_calc.py:5: AssertionError")
    assert failure_message(cut, report) == "AssertionError: noise noise REAL_CAUSE\nassert -1 == 5"
    assert failure_message("assert 1 == 2", report) == "assert 1 == 2"  # untruncated: unchanged
    assert failure_message(None, None) == ""

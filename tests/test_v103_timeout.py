"""A test run that exceeds the time limit is ABSTAIN with a timeout note, not tampering.

The sandbox used a fixed 30 s limit for the whole workspace suite; a slower, correct
suite got FAIL with "COLLECTION TAMPERING DETECTED" and next action restore_tests.
"""

import json

from the_judge.api import verify
from the_judge.core.evidence import DEFAULT_TEST_TIMEOUT
from the_judge.integrations.cli import main


def _slow_project(tmp_path, seconds):
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a + b\n")
    (tmp_path / "test_calc.py").write_text(
        f"import time\nfrom calc import add\n\n\ndef test_add():\n"
        f"    time.sleep({seconds})\n    assert add(2, 3) == 5\n"
    )


def test_default_timeout_allows_realistic_suites():
    assert DEFAULT_TEST_TIMEOUT >= 300


def test_timed_out_run_is_abstain_not_tampering(tmp_path):
    _slow_project(tmp_path, 10)
    result = verify(str(tmp_path), mutation=False, timeout=3)
    assert result.decision == "ABSTAIN", result.blocking_issues
    assert not [b for b in result.blocking_issues if "TAMPERING" in b]
    notes = " ".join(result.insufficient_notes)
    assert "timed out" in notes.lower() and "3" in notes
    assert result.next_actions[0]["action"] != "restore_tests"


def test_timeout_note_points_at_cli_flag(tmp_path, capsys):
    _slow_project(tmp_path, 10)
    code = main(["verify", str(tmp_path), "--json", "--no-mutation", "--timeout", "3"])
    out = json.loads(capsys.readouterr().out)
    assert code == 2
    assert "--timeout" in json.dumps(out["next_actions"]) + " ".join(out["insufficient_notes"])


def test_suite_within_timeout_passes_through(tmp_path):
    _slow_project(tmp_path, 0)
    result = verify(str(tmp_path), mutation=False, timeout=120)
    assert not [n for n in result.insufficient_notes if "timed out" in n.lower()]

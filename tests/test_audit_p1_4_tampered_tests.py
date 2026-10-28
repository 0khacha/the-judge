"""P1-4: tampered, skipped or weakened tests must not yield PASS.

* skipped / xfail tests are non-passing evidence and are reported;
* vacuous assertions (tautologies, `in (True, False)`, `assert True`, `is not None`
  as the only assertion) are not evidence;
* in a git repo, tests deleted, assertions removed or skips added relative to HEAD
  (or --baseline REF) are a blocking tampering finding.
"""

import json
import os
import subprocess
import sys

import pytest

from audit_helpers import corpus_workspace, git, judge, write

TASK = "11_tampered_tests"
TAMPERED = ["tampered_deleted_assert", "tampered_skip", "tampered_tautology"]
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.mark.parametrize("variant", TAMPERED)
def test_tampered_wrong_impl_in_git_repo_is_not_pass(tmp_path, variant):
    result = judge(corpus_workspace(tmp_path, TASK, variant, git_baseline=True))
    assert result.decision != "PASS"
    assert any(f.category == "tampering" for f in result.findings), result.to_dict()["findings"]


@pytest.mark.parametrize("variant, kind", [
    ("tampered_skip", "skipped"), ("tampered_tautology", "vacuous"),
])
def test_tampered_wrong_impl_without_git_is_not_pass(tmp_path, variant, kind):
    # Without a baseline the skip and the tautology are still visible in the file,
    # and must be reported as such (not merely ABSTAINed for an unrelated reason).
    result = judge(corpus_workspace(tmp_path, TASK, variant))
    assert result.decision != "PASS", result.to_dict()
    flagged = [f for f in result.findings
               if kind in f.description.lower()
               and "test_preserves_first_occurrence_order" in f.description]
    assert flagged, [f.description for f in result.findings]


def test_honest_tests_in_git_repo_are_not_flagged(tmp_path):
    ws = corpus_workspace(tmp_path, TASK, "correct", git_baseline=True)
    # Honest edit after the baseline: a new test is added, nothing is weakened.
    with open(os.path.join(ws, "test_dedupe.py"), "a", encoding="utf-8") as f:
        f.write("\n\ndef test_empty():\n    assert dedupe([]) == []\n")
    result = judge(ws)
    assert not any(f.category == "tampering" for f in result.findings)
    assert result.decision != "FAIL", result.blocking_issues


def test_skipped_and_xfail_tests_are_non_passing_and_reported(tmp_path):
    ws = write(tmp_path, {
        "calc.py": "def add(a, b):\n    return a - b\n",
        "test_calc.py": (
            "import pytest\n"
            "from calc import add\n"
            "@pytest.mark.skip(reason='later')\n"
            "def test_add_skipped():\n"
            "    assert add(1, 2) == 3\n"
            "@pytest.mark.xfail\n"
            "def test_add_xfail():\n"
            "    assert add(1, 2) == 3\n"
        ),
    })
    result = judge(ws)
    assert result.decision != "PASS"
    skipped = " ".join(f.description for f in result.findings if "skipped" in f.description.lower())
    assert "test_add_skipped" in skipped and "test_add_xfail" in skipped
    assert result.provenance["passed_tests"] == 0


def test_is_not_none_as_only_assertion_is_not_evidence(tmp_path):
    ws = write(tmp_path, {
        "calc.py": "def add(a, b):\n    return a - b\n",
        "test_calc.py": (
            "from calc import add\n"
            "def test_add():\n"
            "    assert add(1, 2) is not None\n"
        ),
    })
    result = judge(ws)
    assert result.decision != "PASS"
    assert any("vacuous" in f.description.lower() and "test_add" in f.description
               for f in result.findings), [f.description for f in result.findings]


def _git_project(tmp_path):
    ws = write(tmp_path, {
        "calc.py": "def add(a, b):\n    return a + b\n",
        "test_calc.py": (
            "from calc import add\n"
            "def test_add():\n"
            "    assert add(1, 2) == 3\n"
            "    assert add(-1, 1) == 0\n"
            "def test_add_zero():\n"
            "    assert add(0, 0) == 0\n"
        ),
    })
    git(ws, "init", "-q")
    git(ws, "add", "-A")
    git(ws, "commit", "-q", "-m", "baseline")
    return ws


@pytest.mark.parametrize("tampered_test, needle", [
    ("from calc import add\ndef test_add():\n    assert add(1, 2) == 3\n    assert add(-1, 1) == 0\n",
     "test_add_zero"),
    ("from calc import add\ndef test_add():\n    assert add(1, 2) == 3\n"
     "def test_add_zero():\n    assert add(0, 0) == 0\n",
     "test_add"),
    ("import pytest\nfrom calc import add\ndef test_add():\n    assert add(1, 2) == 3\n"
     "    assert add(-1, 1) == 0\n@pytest.mark.skip\ndef test_add_zero():\n    assert add(0, 0) == 0\n",
     "test_add_zero"),
], ids=["deleted_test", "removed_assertion", "added_skip"])
def test_git_baseline_tampering_blocks_pass(tmp_path, tampered_test, needle):
    ws = _git_project(tmp_path)
    write(ws, {"test_calc.py": tampered_test})
    result = judge(ws)
    assert result.decision == "FAIL"
    tampering = [f for f in result.findings if f.category == "tampering"]
    assert tampering and any(needle in f.description for f in tampering)


def test_deleted_test_file_is_tampering(tmp_path):
    ws = _git_project(tmp_path)
    write(ws, {"test_other.py": "from calc import add\ndef test_other():\n    assert add(2, 2) == 4\n"})
    os.remove(os.path.join(ws, "test_calc.py"))
    result = judge(ws)
    assert result.decision == "FAIL"
    assert any(f.category == "tampering" and "test_calc.py" in f.description for f in result.findings)


def test_baseline_ref_option(tmp_path):
    ws = _git_project(tmp_path)
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ws, capture_output=True,
                          stdin=subprocess.DEVNULL,
                          text=True, check=True).stdout.strip()
    write(ws, {"test_calc.py": "from calc import add\ndef test_add():\n    assert add(1, 2) == 3\n"})
    git(ws, "commit", "-q", "-am", "weaken tests")
    # Against HEAD the weakening is already committed, so nothing is flagged...
    assert not any(f.category == "tampering" for f in judge(ws).findings)
    # ...but against the explicit baseline it is, via the API and the CLI.
    from the_judge.api import verify

    assert verify(ws, baseline=base).decision == "FAIL"
    launcher = (
        "import sys; sys.path.insert(0, sys.argv.pop(1)); "
        "from the_judge.integrations.cli import main; sys.exit(main(sys.argv[1:]))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", launcher, REPO, "verify", ws, "--json", "--baseline", base],
        capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=600,
    )
    data = json.loads(proc.stdout[proc.stdout.index("{"):])
    assert proc.returncode == 1 and data["decision"] == "FAIL"
    assert any(f["category"] == "tampering" for f in data["findings"])

"""Runtime requirements: the judge runs tests with `python -m pytest`.

* pytest must be a declared dependency, or a PyPI install cannot verify anything;
* if the test runner cannot start anyway, that is an infrastructure problem: the
  verdict must not be FAIL and must not accuse the code of tampering.
"""

import json
import os
import re
import subprocess
import sys

from audit_helpers import corpus_workspace

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_pytest_is_a_runtime_dependency():
    with open(os.path.join(REPO, "pyproject.toml"), encoding="utf-8") as f:
        pyproject = f.read()
    deps = re.search(r"^dependencies = \[(.*?)\]", pyproject, re.M | re.S).group(1)
    assert re.search(r"[\"']pytest[>=<~! ]", deps), deps


def test_missing_test_runner_is_not_a_fail_or_tampering(tmp_path):
    venv = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(venv)], check=True,
                   capture_output=True, stdin=subprocess.DEVNULL)
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    ws = corpus_workspace(tmp_path / "ws", "04_nested_transactions")
    launcher = (
        "import sys; sys.path.insert(0, sys.argv.pop(1)); "
        "from the_judge.integrations.cli import main; sys.exit(main(sys.argv[1:]))"
    )
    proc = subprocess.run(
        [str(python), "-c", launcher, REPO, "verify", ws, "--json"],
        capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=600,
        env=dict(os.environ, PYTHONPATH=REPO),
    )
    data = json.loads(proc.stdout[proc.stdout.index("{"):])
    assert data["decision"] == "ABSTAIN", data["blocking_issues"]
    assert proc.returncode == 2
    assert not any("TAMPERING" in b for b in data["blocking_issues"])
    assert any("pytest" in n for n in data["insufficient_notes"]), data["insufficient_notes"]

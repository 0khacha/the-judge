"""The PostToolUse hook must report a FAIL verdict (exit 1, findings on stderr).

Findings are ``Finding`` dataclasses; the hook used to call ``.get()`` on them,
which raised inside the never-crash handler and turned every FAIL into exit 0.
"""

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run_hook(cwd, command="python -m pytest"):
    env = dict(os.environ, PYTHONPATH=ROOT)
    return subprocess.run(
        [sys.executable, "-m", "the_judge.hook"],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(cwd),
        env=env,
    )


def test_hook_fail_verdict_exits_one_and_lists_findings(tmp_path):
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a - b\n")
    (tmp_path / "test_calc.py").write_text(
        "from calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n"
    )
    result = _run_hook(tmp_path)
    assert "Hook error" not in result.stderr, result.stderr
    assert result.returncode == 1, result.stderr
    assert "DECISION: FAIL" in result.stderr
    assert "test_add" in result.stderr

"""`judge improve`: a read-only review by default, an agent-driven loop with --agent.

The agent here is a small Python script standing in for a coding agent: it reads the
prompt on stdin (or from {prompt_file}) and edits the workspace.
"""

import hashlib
import os
import sys

import pytest

from the_judge.api import freeze, improve
from the_judge.integrations.agent_runner import (
    build_prompt,
    resolve_agent_command,
    run_agent,
)
from the_judge.integrations.cli import main

STUB = "def add(a, b):\n    raise NotImplementedError\n"
BUGGY = "def add(a, b):\n    return a - b\n"
TESTS = (
    "from calc import add\n\n\n"
    "def test_add():\n    assert add(2, 3) == 5\n\n\n"
    "def test_add_negative():\n    assert add(-2, -7) == -9\n"
)
FIXER = (
    "import sys, pathlib\n"
    "prompt = sys.stdin.read()\n"
    "pathlib.Path('prompt_seen.txt').write_text(prompt, encoding='utf-8')\n"
    "pathlib.Path('calc.py').write_text('def add(a, b):\\n    return a + b\\n')\n"
)


def _snapshot(root):
    out = {}
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(("_judge", ".judge", "__pycache__"))]
        for name in files:
            path = os.path.join(dirpath, name)
            with open(path, "rb") as f:
                out[os.path.relpath(path, root)] = hashlib.sha256(f.read()).hexdigest()
    return out


def _project(tmp_path):
    """Tests frozen against a stub, then a buggy implementation: the usual FAIL."""
    (tmp_path / "calc.py").write_text(STUB)
    (tmp_path / "test_calc.py").write_text(TESTS)
    freeze(str(tmp_path))
    (tmp_path / "calc.py").write_text(BUGGY)
    return tmp_path


def _agent(tmp_path, source):
    script = tmp_path.parent / f"agent_{tmp_path.name}.py"
    script.write_text(source)
    return f'"{sys.executable}" "{script}"'


def test_review_does_not_modify_workspace(tmp_path):
    ws = _project(tmp_path)
    before = _snapshot(ws)
    result = improve(workspace=str(ws), max_rounds=3)
    assert _snapshot(ws) == before
    assert result["outcome"] == "REVIEW_ONLY"
    assert result["total_rounds"] == 1
    assert result["final_decision"] == "FAIL"
    assert result["next_actions"][0]["action"] == "fix_code"
    assert "--agent" in result["reason"]


def test_cli_review_prints_next_actions_and_exits_with_verdict(tmp_path, capsys):
    ws = _project(tmp_path)
    code = main(["improve", str(ws), "--no-report"])
    out = capsys.readouterr().out
    assert code == 1  # FAIL, same exit code as judge verify
    assert "REVIEW_ONLY" in out
    assert "[fix_code]" in out
    assert "Evidence       :" not in out  # the old, contradictory label


def test_agent_loop_reaches_pass(tmp_path):
    ws = _project(tmp_path)
    result = improve(workspace=str(ws), max_rounds=3, agent_command=_agent(tmp_path, FIXER))
    assert result["outcome"] == "PASS", result.get("reason")
    assert result["final_decision"] == "PASS"
    assert result["total_rounds"] == 2
    prompt = (ws / "prompt_seen.txt").read_text(encoding="utf-8")
    assert "[fix_code]" in prompt
    assert "test_add" in prompt
    assert ".judge/frozen.json" in prompt  # the agent is told not to touch frozen tests


def test_cli_agent_loop_exits_zero_on_pass(tmp_path, capsys):
    ws = _project(tmp_path)
    code = main(["improve", str(ws), "--no-report", "--agent", _agent(tmp_path, FIXER)])
    out = capsys.readouterr().out
    assert code == 0, out
    assert "RESULT  : PASS" in out


def test_failing_agent_aborts_the_loop(tmp_path):
    ws = _project(tmp_path)
    cmd = _agent(tmp_path, "import sys\nsys.stdin.read()\nsys.exit(4)\n")
    result = improve(workspace=str(ws), max_rounds=3, agent_command=cmd)
    assert result["outcome"] == "ABORTED"
    assert "exited with code 4" in result["history"][0]["repair"]["summary"]


def test_agent_that_changes_nothing_stops_the_loop(tmp_path):
    ws = _project(tmp_path)
    cmd = _agent(tmp_path, "import sys\nsys.stdin.read()\n")
    result = improve(workspace=str(ws), max_rounds=3, agent_command=cmd)
    assert result["outcome"] == "NO_MEANINGFUL_IMPROVEMENT"


def test_apply_was_removed_with_a_pointer_to_agent(tmp_path, capsys):
    with pytest.raises(ValueError, match="agent_command"):
        improve(workspace=str(tmp_path), apply=True)
    assert main(["improve", str(tmp_path), "--apply"]) == 3
    assert "--agent" in capsys.readouterr().err


def test_prompt_file_placeholder(tmp_path):
    script = tmp_path / "reader.py"
    script.write_text("import sys, pathlib\n"
                      "pathlib.Path('got.txt').write_text(pathlib.Path(sys.argv[1]).read_text())\n")
    out = run_agent(f'"{sys.executable}" "{script}" {{prompt_file}}', "hello agent", str(tmp_path))
    assert out["exit_code"] == 0
    assert (tmp_path / "got.txt").read_text() == "hello agent"


def test_build_prompt_orders_actions_and_skips_bookkeeping():
    prompt = build_prompt({
        "decision": "ABSTAIN", "numeric_score": 65.0,
        "next_actions": [
            {"step": 1, "action": "add_test", "detail": "cache.py:45: '>' -> '>='",
             "guidance": "Decide from the spec."},
            {"step": 2, "action": "re_verify", "detail": "verify again"},
        ],
        "findings": [],
    })
    assert "Verdict: ABSTAIN (score 65.0/100)" in prompt
    assert "1. [add_test] cache.py:45" in prompt
    assert "Decide from the spec." in prompt
    assert "re_verify" not in prompt


def test_auto_agent_without_known_agent_is_an_error(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    with pytest.raises(ValueError, match="No coding agent found"):
        resolve_agent_command("auto")
    assert resolve_agent_command("my-agent --go") == "my-agent --go"

"""Claude Code hook: verify before the agent stops, send the work back unless PASS."""

import json
import os
import subprocess
import sys

from audit_helpers import repo_root

from the_judge.api import freeze

STUB = "def add(a, b):\n    raise NotImplementedError\n"
TESTS = "from calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n"


def _hook(cwd, payload=None, env_extra=None):
    payload = payload if payload is not None else {"hook_event_name": "Stop",
                                                   "stop_hook_active": False,
                                                   "cwd": str(cwd)}
    env = {k: v for k, v in os.environ.items() if k != "THE_JUDGE_HOOK"}
    env.update(PYTHONPATH=repo_root(), **(env_extra or {}))
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    res = subprocess.run([sys.executable, "-m", "the_judge.hook"], input=raw,
                         capture_output=True, text=True, timeout=300, cwd=str(cwd), env=env)
    out = json.loads(res.stdout) if res.stdout.strip() else None
    return res, out


def _project(tmp_path, code):
    (tmp_path / "calc.py").write_text(STUB)
    (tmp_path / "test_calc.py").write_text(TESTS)
    freeze(str(tmp_path))
    (tmp_path / "calc.py").write_text(code)
    return tmp_path


def test_fail_blocks_stop_with_next_actions(tmp_path):
    ws = _project(tmp_path, "def add(a, b):\n    return a - b\n")
    res, out = _hook(ws)
    assert res.returncode == 0, res.stderr
    assert out["decision"] == "block"
    assert "Verdict: FAIL" in out["reason"]
    assert "[fix_code]" in out["reason"] and "test_add" in out["reason"]


def test_unchanged_workspace_is_not_verified_again(tmp_path):
    ws = _project(tmp_path, "def add(a, b):\n    return a - b\n")
    _hook(ws)
    res, out = _hook(ws, {"hook_event_name": "Stop", "stop_hook_active": True, "cwd": str(ws)})
    assert res.returncode == 0
    assert out is None  # nothing changed: the agent may stop


def test_pass_lets_the_agent_stop(tmp_path):
    ws = _project(tmp_path, "def add(a, b):\n    return a + b\n")
    res, out = _hook(ws)
    assert res.returncode == 0, res.stderr
    assert "decision" not in out
    assert "PASS" in out["systemMessage"]
    state = json.loads((ws / ".judge" / "hook_state.json").read_text())
    assert state["decision"] == "PASS"


def test_project_without_judge_state_is_ignored(tmp_path):
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a - b\n")
    (tmp_path / "test_calc.py").write_text(TESTS)
    res, out = _hook(tmp_path)
    assert res.returncode == 0 and out is None
    assert not (tmp_path / ".judge").exists()


def test_hook_can_be_forced_on_and_off(tmp_path):
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a - b\n")
    (tmp_path / "test_calc.py").write_text(TESTS)
    _, out = _hook(tmp_path, env_extra={"THE_JUDGE_HOOK": "always"})
    assert out["decision"] == "block"
    (tmp_path / "w").mkdir()
    ws = _project(tmp_path / "w", "def add(a, b):\n    return a - b\n")
    _, out = _hook(ws, env_extra={"THE_JUDGE_HOOK": "off"})
    assert out is None


def test_other_events_and_tools_are_ignored(tmp_path):
    ws = _project(tmp_path, "def add(a, b):\n    return a - b\n")
    for payload in ({"hook_event_name": "UserPromptSubmit", "cwd": str(ws)},
                    {"hook_event_name": "PostToolUse", "tool_name": "Read", "cwd": str(ws)}):
        res, out = _hook(ws, payload)
        assert res.returncode == 0 and out is None


def test_bad_input_never_breaks_the_agent(tmp_path):
    for raw in ("", "not json", "[1, 2]"):
        res, out = _hook(tmp_path, raw)
        assert res.returncode == 0 and out is None


def test_hook_run_subcommand_exists():
    from the_judge.integrations.cli import main

    try:
        code = main(["hook", "run", "--help"])
    except SystemExit as e:
        code = e.code
    assert code == 0


def _hook_commands(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return [h["command"] for group in data["hooks"]["Stop"] for h in group["hooks"]]


def test_plugin_and_project_settings_register_the_stop_hook():
    assert _hook_commands(os.path.join(repo_root(), "plugin", "hooks", "hooks.json")) == ["judge hook run"]
    assert _hook_commands(os.path.join(repo_root(), ".claude", "settings.json")) == [
        "python -m the_judge.hook"]


def test_plugin_manifest_version_matches_package():
    from the_judge._version import __version__

    with open(os.path.join(repo_root(), "plugin", ".claude-plugin", "plugin.json"), encoding="utf-8") as f:
        manifest = json.load(f)
    assert manifest["name"] == "the-judge"
    assert manifest["version"] == __version__


def test_marketplace_points_at_the_plugin_folder():
    with open(os.path.join(repo_root(), ".claude-plugin", "marketplace.json"), encoding="utf-8") as f:
        market = json.load(f)
    entry = market["plugins"][0]
    assert entry["name"] == "the-judge"
    assert os.path.isfile(os.path.join(repo_root(), entry["source"], ".claude-plugin", "plugin.json"))

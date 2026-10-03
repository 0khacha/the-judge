"""Regression tests for Bug 4: broken Claude Code hook.

.claude/settings.json runs `py -m judge.hook` but the module doesn't exist.
Tests that the_judge.hook module exists, reads PostToolUse JSON from stdin,
runs verification only for code-changing commands, and never crashes.
"""

import json
import subprocess
import sys
import os

import pytest


class TestBug4Hook:
    """the_judge.hook must exist, handle stdin JSON, and never crash."""

    def test_hook_module_exists(self):
        """the_judge.hook must be importable."""
        import the_judge.hook  # noqa: F401

    def test_hook_run_subcommand_exists(self):
        """'judge hook run' subcommand must be registered."""
        from the_judge.integrations.cli import main

        # --help causes SystemExit(0) from argparse
        try:
            exit_code = main(["hook", "run", "--help"])
        except SystemExit as e:
            exit_code = e.code
        assert exit_code == 0

    def test_hook_non_code_command_exits_zero(self):
        """Hook receiving a non-code-changing command should exit 0 silently."""
        hook_input = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la"},
            "tool_result": "total 0"
        })
        result = subprocess.run(
            [sys.executable, "-m", "the_judge.hook"],
            input=hook_input,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        assert result.returncode == 0, (
            f"Hook should exit 0 for non-code command, got {result.returncode}"
        )

    def test_hook_code_changing_command_processes(self):
        """Hook receiving a code-changing command should attempt verification."""
        hook_input = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "python -m pytest tests/"},
            "tool_result": "1 passed"
        })
        result = subprocess.run(
            [sys.executable, "-m", "the_judge.hook"],
            input=hook_input,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        # Should never crash — exit 0 unless FAIL
        assert result.returncode in (0, 1), (
            f"Hook should exit 0 or 1, got {result.returncode}. "
            f"stderr: {result.stderr[:500]}"
        )

    def test_hook_malformed_json_exits_zero(self):
        """Hook receiving invalid JSON should exit 0 (never crash the agent)."""
        result = subprocess.run(
            [sys.executable, "-m", "the_judge.hook"],
            input="not json at all",
            capture_output=True,
            text=True,
            timeout=10,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        assert result.returncode == 0, (
            f"Hook should exit 0 on malformed JSON, got {result.returncode}"
        )

    def test_hook_empty_stdin_exits_zero(self):
        """Hook receiving empty stdin should exit 0."""
        result = subprocess.run(
            [sys.executable, "-m", "the_judge.hook"],
            input="",
            capture_output=True,
            text=True,
            timeout=10,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        assert result.returncode == 0

    def test_settings_json_uses_cross_platform_command(self):
        """settings.json must use python -m the_judge.hook (not py -m judge.hook)."""
        settings_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".claude", "settings.json"
        )
        if not os.path.exists(settings_path):
            pytest.skip("No .claude/settings.json found")

        with open(settings_path, encoding="utf-8") as f:
            data = json.load(f)

        hooks = data.get("hooks", {}).get("PostToolUse", [])
        for hook_group in hooks:
            for hook in hook_group.get("hooks", []):
                cmd = hook.get("command", "")
                assert "py -m judge.hook" not in cmd, (
                    f"settings.json still uses 'py -m judge.hook': {cmd}"
                )

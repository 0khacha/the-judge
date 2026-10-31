"""Claude Code hook: verify the work before the agent stops, and send it back if needed.

Claude Code runs this on the ``Stop`` event (and, for older setups, ``PostToolUse``)
with the event as JSON on stdin. The hook

1. acts only in projects that use The Judge: a ``.judge/`` directory exists (created by
   ``judge freeze``), or THE_JUDGE_HOOK=always is set;
2. verifies only when source or test files changed since the hook last verified, so a
   turn without code changes costs nothing;
3. on PASS lets the agent stop; on FAIL or ABSTAIN prints
   ``{"decision": "block", "reason": ...}`` so Claude Code hands the judge's
   ``next_actions`` back to the agent, which keeps working;
4. lets the agent stop when the judge reports the loop as stuck (3 identical results or
   5 runs without PASS, see .judge/history.json) and tells the user why.

It never crashes the agent: any internal error is reported on stderr and exit code 0.

Usage:
    python -m the_judge.hook          # reads the hook event JSON from stdin
    judge hook run                    # same
"""

import hashlib
import json
import os
import sys
from typing import Any

STATE_FILE = "hook_state.json"
_SOURCE_EXTENSIONS = (".py", ".pyi", ".json", ".toml", ".cfg", ".ini", ".md", ".txt",
                      ".html", ".css", ".js", ".ts")
_IGNORED_DIRS = frozenset({".git", ".hg", ".svn", ".judge", "__pycache__", ".venv", "venv",
                           "env", "node_modules", ".mypy_cache", ".pytest_cache",
                           ".ruff_cache", "_judge_report", "_judge_visual", "dist", "build"})


def _enabled(workspace: str) -> bool:
    mode = os.environ.get("THE_JUDGE_HOOK", "").strip().lower()
    if mode in ("0", "off", "false", "never"):
        return False
    if mode in ("1", "on", "true", "always"):
        return True
    return os.path.isdir(os.path.join(workspace, ".judge"))


def workspace_fingerprint(workspace: str) -> str:
    """Hash of the project's source, test and spec files (judge state excluded)."""
    hasher = hashlib.sha256()
    for root, dirs, files in os.walk(workspace):
        dirs[:] = sorted(d for d in dirs if d not in _IGNORED_DIRS and not d.endswith(".egg-info"))
        for name in sorted(files):
            if not name.endswith(_SOURCE_EXTENSIONS):
                continue
            path = os.path.join(root, name)
            hasher.update(os.path.relpath(path, workspace).replace(os.sep, "/").encode("utf-8"))
            try:
                with open(path, "rb") as fh:
                    hasher.update(fh.read())
            except OSError:
                continue
    return hasher.hexdigest()


def _load_state(workspace: str) -> dict[str, Any]:
    try:
        with open(os.path.join(workspace, ".judge", STATE_FILE), encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_state(workspace: str, state: dict[str, Any]) -> None:
    os.makedirs(os.path.join(workspace, ".judge"), exist_ok=True)
    with open(os.path.join(workspace, ".judge", STATE_FILE), "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2)


def _reason(result: Any) -> str:
    """The text handed back to the agent: verdict, next actions and the rules."""
    from the_judge.integrations.agent_runner import build_prompt

    prompt = build_prompt(result.to_dict())
    return (prompt + "\n\nAfter the changes, finish your turn; the judge verifies again "
            "(or run `judge verify . --json` yourself).")


def check(workspace: str) -> dict[str, Any] | None:
    """Verify ``workspace`` if it changed; return the hook output, or None to allow."""
    if not _enabled(workspace):
        return None

    fingerprint = workspace_fingerprint(workspace)
    state = _load_state(workspace)
    if state.get("fingerprint") == fingerprint:
        # Nothing changed since the last verification. Asking again would only repeat
        # the same feedback, so let the agent stop.
        return None

    from the_judge.api import verify
    from the_judge.integrations.cli import _find_task_spec, _load_task_spec

    task_spec = _load_task_spec(_find_task_spec(workspace, None))
    result = verify(workspace=workspace, task_spec=task_spec, record_history=True)
    _save_state(workspace, {"fingerprint": fingerprint, "decision": result.decision,
                            "score": result.numeric_score})

    if result.decision == "PASS":
        return {"systemMessage": f"The Judge: PASS (score {result.numeric_score:.1f})."}

    loop = result.loop or {}
    first = (result.next_actions or [{}])[0]
    if loop.get("stuck") or first.get("action") == "stop":
        reason = loop.get("stuck_reason") or first.get("detail", "")
        return {"systemMessage": f"The Judge: {result.decision} (score "
                f"{result.numeric_score:.1f}); the repair loop is stuck and was not "
                f"continued: {reason}"}

    return {"decision": "block", "reason": _reason(result)}


def run_hook() -> int:
    """Main hook entry point. Always returns 0; the verdict travels in the JSON output."""
    try:
        from the_judge.integrations.cli import use_utf8_output

        use_utf8_output()
        raw = sys.stdin.read()
        if not raw.strip():
            return 0
        try:
            data = json.loads(raw)
        except ValueError:
            return 0
        if not isinstance(data, dict):
            return 0

        event = data.get("hook_event_name") or ("PostToolUse" if data.get("tool_name") else "Stop")
        if event == "PostToolUse" and data.get("tool_name") not in ("Bash", "Edit", "Write",
                                                                    "MultiEdit", "NotebookEdit"):
            return 0
        if event not in ("Stop", "SubagentStop", "PostToolUse"):
            return 0

        workspace = os.path.abspath(data.get("cwd") or os.getcwd())
        output = check(workspace)
        if output:
            print(json.dumps(output))
    except Exception as exc:  # never break the agent
        print(f"[The Judge] hook error (ignored): {exc}", file=sys.stderr)
    return 0


def main() -> None:
    """Entry point for python -m the_judge.hook."""
    sys.exit(run_hook())


if __name__ == "__main__":
    main()

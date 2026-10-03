"""PostToolUse hook for Claude Code / AI agent integration.

Reads PostToolUse JSON from stdin, runs verification only when the
command appears to be code-changing or test-related.  Never crashes
the agent: catches all exceptions, exits 0 unless verification
returns FAIL, and prints findings to stderr.

Usage:
    python -m the_judge.hook          # reads JSON from stdin
    judge hook run                    # CLI subcommand (same behavior)
"""

import json
import os
import sys


# Patterns that indicate a code-changing or test-related command
_CODE_PATTERNS = (
    "pytest", "python -m pytest", "py -m pytest",
    "python ", "py ",
    "pip install", "pip3 install",
    "git commit", "git push",
    "make", "tox", "nox",
)

_CODE_EXTENSIONS = (".py", ".js", ".ts", ".go", ".rs", ".java", ".c", ".cpp")


def _is_code_changing_command(command: str) -> bool:
    """Return True if the command looks code-changing or test-related."""
    cmd_lower = command.lower().strip()

    # Check for known patterns
    for pat in _CODE_PATTERNS:
        if pat in cmd_lower:
            return True

    # Check for file editing commands that touch code files
    for ext in _CODE_EXTENSIONS:
        if ext in cmd_lower:
            return True

    # Writing to files (echo/cat/tee redirection)
    if ">" in command and any(ext in command for ext in _CODE_EXTENSIONS):
        return True

    return False


def run_hook() -> int:
    """Main hook entry point. Returns exit code (0 or 1)."""
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return 0

        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return 0

        tool_name = data.get("tool_name", "")
        tool_input = data.get("tool_input", {})

        # Only process Bash tool invocations
        if tool_name != "Bash":
            return 0

        command = tool_input.get("command", "")
        if not command:
            return 0

        # Skip non-code-changing commands (ls, cd, cat, etc.)
        if not _is_code_changing_command(command):
            return 0

        # Run verification on current directory
        try:
            from the_judge.api import verify

            result = verify(workspace=os.getcwd())

            if result.decision == "FAIL":
                # Print findings to stderr so the agent can see them
                print(
                    f"[The Judge] DECISION: {result.decision} "
                    f"(score: {result.numeric_score})",
                    file=sys.stderr,
                )
                for finding in result.findings:
                    desc = finding.get("description", "")
                    focus = finding.get("suggested_focus", "")
                    print(f"  - {desc}", file=sys.stderr)
                    if focus:
                        print(f"    Focus: {focus}", file=sys.stderr)
                for issue in result.blocking_issues:
                    print(f"  BLOCKING: {issue}", file=sys.stderr)
                return 1

            # Non-FAIL decisions: print summary to stderr but exit 0
            if result.decision != "PASS":
                print(
                    f"[The Judge] DECISION: {result.decision} "
                    f"(score: {result.numeric_score})",
                    file=sys.stderr,
                )

        except Exception as e:
            # Never crash the agent — log and continue
            print(f"[The Judge] Hook error (non-fatal): {e}", file=sys.stderr)

    except Exception:
        # Catch-all: never crash
        pass

    return 0


def main() -> None:
    """Entry point for python -m the_judge.hook."""
    sys.exit(run_hook())


if __name__ == "__main__":
    main()

"""Git hook management for The Judge.

Installs / uninstalls pre-commit and pre-push hooks that run
`judge verify .` and block on failure.
"""

import os
import stat
from typing import Optional

PRE_COMMIT_TEMPLATE = """#!/bin/sh
# The Judge -- pre-commit verification hook
# Installed by: judge hook install
# Remove with:  judge hook uninstall

echo "The Judge: verifying workspace before commit..."
judge verify . --json > /dev/null 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "The Judge: PASS -- commit allowed."
    exit 0
elif [ $EXIT_CODE -eq 1 ]; then
    echo "The Judge: FAIL -- commit blocked. Run 'judge verify .' for details."
    exit 1
elif [ $EXIT_CODE -eq 2 ]; then
    echo "The Judge: ABSTAIN -- insufficient evidence. Commit blocked."
    exit 1
else
    echo "The Judge: ERROR -- verification could not run. Commit allowed."
    exit 0
fi
"""

PRE_PUSH_TEMPLATE = """#!/bin/sh
# The Judge -- pre-push verification hook
# Installed by: judge hook install --pre-push
# Remove with:  judge hook uninstall --pre-push

echo "The Judge: verifying workspace before push..."
judge verify . --json > /dev/null 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "The Judge: PASS -- push allowed."
    exit 0
elif [ $EXIT_CODE -eq 1 ]; then
    echo "The Judge: FAIL -- push blocked. Run 'judge verify .' for details."
    exit 1
elif [ $EXIT_CODE -eq 2 ]; then
    echo "The Judge: ABSTAIN -- insufficient evidence. Push blocked."
    exit 1
else
    echo "The Judge: ERROR -- verification could not run. Push allowed."
    exit 0
fi
"""

HOOK_MARKER = "# Installed by: judge hook"


def _find_git_dir(workspace: str) -> Optional[str]:
    """Walk up from workspace to find .git directory."""
    current = os.path.abspath(workspace)
    while True:
        candidate = os.path.join(current, ".git")
        if os.path.isdir(candidate):
            return candidate
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def install_hook(workspace: str, hook_type: str = "pre-commit") -> str:
    """Install a git hook that runs The Judge before commit or push.

    Args:
        workspace: Path to the workspace (or any directory inside the repo).
        hook_type: Either 'pre-commit' or 'pre-push'.

    Returns:
        Path to the installed hook file.

    Raises:
        FileNotFoundError: If no .git directory is found.
        FileExistsError: If a non-Judge hook already exists at the target path.
    """
    git_dir = _find_git_dir(workspace)
    if not git_dir:
        raise FileNotFoundError(
            f"No .git directory found above {workspace}. "
            "Run this command from inside a git repository."
        )

    hooks_dir = os.path.join(git_dir, "hooks")
    os.makedirs(hooks_dir, exist_ok=True)

    hook_path = os.path.join(hooks_dir, hook_type)

    # Check for existing non-Judge hook
    if os.path.exists(hook_path):
        with open(hook_path, encoding="utf-8") as f:
            content = f.read()
        if HOOK_MARKER not in content:
            raise FileExistsError(
                f"A {hook_type} hook already exists at {hook_path} and was not "
                "installed by The Judge. Remove it manually or use a different hook type."
            )

    template = PRE_PUSH_TEMPLATE if hook_type == "pre-push" else PRE_COMMIT_TEMPLATE

    with open(hook_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(template)

    # Make executable on Unix
    st = os.stat(hook_path)
    os.chmod(hook_path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    return hook_path


def uninstall_hook(workspace: str, hook_type: str = "pre-commit") -> Optional[str]:
    """Remove a Judge-installed git hook.

    Args:
        workspace: Path to the workspace.
        hook_type: Either 'pre-commit' or 'pre-push'.

    Returns:
        Path to the removed hook, or None if no Judge hook was found.
    """
    git_dir = _find_git_dir(workspace)
    if not git_dir:
        return None

    hook_path = os.path.join(git_dir, "hooks", hook_type)

    if not os.path.exists(hook_path):
        return None

    with open(hook_path, encoding="utf-8") as f:
        content = f.read()

    if HOOK_MARKER not in content:
        return None

    os.remove(hook_path)
    return hook_path

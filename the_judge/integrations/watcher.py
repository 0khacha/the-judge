"""File watcher for The Judge.

Polls for .py file changes and re-runs verification automatically.
Zero external dependencies -- uses os.stat polling.
"""

import os
import sys
import time
from typing import Callable, Dict, Optional, Set


def _collect_py_files(directory: str) -> Dict[str, float]:
    """Collect all .py files and their modification times."""
    files = {}
    for root, dirs, filenames in os.walk(directory):
        # Skip hidden directories, __pycache__, .git, venv
        dirs[:] = [
            d for d in dirs
            if not d.startswith(".")
            and d != "__pycache__"
            and d not in ("venv", ".venv", "env", "node_modules")
        ]
        for fname in filenames:
            if fname.endswith(".py"):
                fpath = os.path.join(root, fname)
                try:
                    files[fpath] = os.stat(fpath).st_mtime
                except OSError:
                    pass
    return files


def _detect_changes(
    old_state: Dict[str, float], new_state: Dict[str, float]
) -> Set[str]:
    """Return set of file paths that were added, modified, or deleted."""
    changed = set()

    for path, mtime in new_state.items():
        if path not in old_state or old_state[path] != mtime:
            changed.add(path)

    for path in old_state:
        if path not in new_state:
            changed.add(path)

    return changed


def watch_workspace(
    workspace: str,
    debounce_seconds: float = 2.0,
    on_change: Optional[Callable[[Set[str]], None]] = None,
) -> None:
    """Watch a workspace directory and re-verify on .py file changes.

    Args:
        workspace: Directory to watch.
        debounce_seconds: Seconds to wait after detecting a change before verifying.
        on_change: Optional callback receiving the set of changed file paths.
                   If None, runs the default verification and prints results.
    """
    workspace = os.path.abspath(workspace)

    if on_change is None:
        on_change = _default_verify_callback

    print(f"The Judge: watching {workspace}")
    print(f"           debounce: {debounce_seconds}s")
    print(f"           press Ctrl+C to stop")
    print()

    # Initial scan
    state = _collect_py_files(workspace)
    print(f"Tracking {len(state)} Python files.")
    print()

    # Run initial verification
    print("--- Initial verification ---")
    on_change(set())
    print()

    try:
        while True:
            time.sleep(debounce_seconds)
            new_state = _collect_py_files(workspace)
            changed = _detect_changes(state, new_state)

            if changed:
                timestamp = time.strftime("%H:%M:%S")
                short_names = [os.path.basename(p) for p in sorted(changed)]
                display = ", ".join(short_names[:5])
                if len(short_names) > 5:
                    display += f" (+{len(short_names) - 5} more)"

                print(f"[{timestamp}] Changed: {display}")
                on_change(changed)
                print()

                state = new_state

    except KeyboardInterrupt:
        print("\nThe Judge: watch stopped.")


def _default_verify_callback(changed_files: Set[str]) -> None:
    """Default callback: runs judge verify and prints the result."""
    try:
        from the_judge.api import verify

        result = verify(".")
        decision = result.decision
        score = result.numeric_score

        if decision == "PASS":
            print(f"  PASS  ({score}/100)")
        elif decision == "FAIL":
            print(f"  FAIL  ({score}/100)")
            for idx, f in enumerate(result.findings[:5], 1):
                print(f"    [{idx}] {f.description}")
                if f.suggested_focus:
                    print(f"        -> {f.suggested_focus}")
        elif decision == "ABSTAIN":
            print(f"  ABSTAIN  ({score}/100)")
            for note in result.insufficient_notes[:3]:
                print(f"    - {note}")
        else:
            print(f"  {decision}  ({score}/100)")

    except Exception as e:
        print(f"  ERROR: {e}")

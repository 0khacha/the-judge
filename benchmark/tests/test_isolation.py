"""
test_isolation.py — Unit tests for workspace isolation in benchmark runners.
"""
import os
import shutil
import tempfile
import pytest

from benchmark.agent.agent_interface import WorkspaceToolExecutor


def test_workspace_executor_bounds():
    with tempfile.TemporaryDirectory() as td:
        executor = WorkspaceToolExecutor(td)

        # Writing and viewing inside workspace works
        executor.write_file("sub/test.py", "print('hello')\n")
        content = executor.view_file("sub/test.py")
        assert "print('hello')" in content

        # Escaping workspace with ../ raises PermissionError
        with pytest.raises(PermissionError):
            executor.view_file("../../outside.txt")

        with pytest.raises(PermissionError):
            executor.write_file("../outside.txt", "hacked")


def test_source_task_immutability():
    """Verify that operations on a trial workspace do not alter the source task template."""
    with tempfile.TemporaryDirectory() as src_dir:
        test_file = os.path.join(src_dir, "original.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("# original code\n")

        # Create trial copy
        with tempfile.TemporaryDirectory() as trial_base:
            trial_ws = os.path.join(trial_base, "task")
            shutil.copytree(src_dir, trial_ws)

            # Modify trial copy
            mod_file = os.path.join(trial_ws, "original.py")
            with open(mod_file, "w", encoding="utf-8") as f:
                f.write("# heavily modified code\n")

            # Verify trial copy changed
            with open(mod_file, "r", encoding="utf-8") as f:
                assert "heavily modified" in f.read()

        # Verify source directory remains completely unchanged
        with open(test_file, "r", encoding="utf-8") as f:
            assert f.read() == "# original code\n"

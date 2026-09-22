"""
test_physical_isolation.py — Unit tests verifying physical isolation of hidden tests and oracle scripts.
"""
import os
import shutil
import tempfile
import pytest


def test_physical_exclusion_of_oracle_and_hidden_tests():
    """Verify the physical isolation protocol used in Level 2 trials."""
    with tempfile.TemporaryDirectory() as temp_base:
        src_task = os.path.join(temp_base, "src_task")
        os.makedirs(src_task)

        # Create dummy task contents
        with open(os.path.join(src_task, "module.py"), "w") as f:
            f.write("def solve(): return 42\n")
        with open(os.path.join(src_task, "apply_fix.py"), "w") as f:
            f.write("print('oracle patch')\n")
        
        hidden_dir = os.path.join(src_task, "hidden_tests")
        os.makedirs(hidden_dir)
        with open(os.path.join(hidden_dir, "test_hidden.py"), "w") as f:
            f.write("def test_secret(): assert True\n")

        # Execute isolation protocol
        agent_ws = os.path.join(temp_base, "agent_ws")
        eval_ws = os.path.join(temp_base, "eval_ws")
        shutil.copytree(src_task, agent_ws)
        os.makedirs(eval_ws, exist_ok=True)

        # 1. Remove apply_fix.py
        oracle_f = os.path.join(agent_ws, "apply_fix.py")
        if os.path.exists(oracle_f):
            os.remove(oracle_f)

        # 2. Move hidden_tests
        src_h = os.path.join(agent_ws, "hidden_tests")
        dst_h = os.path.join(eval_ws, "hidden_tests")
        if os.path.exists(src_h):
            shutil.move(src_h, dst_h)

        # Invariant checks:
        # Agent workspace must NOT contain oracle or hidden tests
        assert not os.path.exists(os.path.join(agent_ws, "apply_fix.py"))
        assert not os.path.exists(os.path.join(agent_ws, "hidden_tests"))
        assert os.path.exists(os.path.join(agent_ws, "module.py"))

        # Evaluator workspace contains hidden tests
        assert os.path.exists(os.path.join(eval_ws, "hidden_tests", "test_hidden.py"))

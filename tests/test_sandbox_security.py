"""Sandbox Security Test Suite for The Judge v3.

Tests whether SandboxRunner effectively prevents untrusted target implementations from
detecting evaluation context via sys.argv, os.environ, inspect.stack(), filesystem paths,
sys.modules, process tree, or temporary directory names.
"""

import os
import sys
import tempfile
import pytest
from judge.sandbox import SandboxRunner


def test_attack_a_argv_detection(tmp_path):
    """Target checks sys.argv for evaluation keywords like '_synthesized_tests' or 'judge'."""
    task_dir = str(tmp_path)
    
    # Target file that returns DETECTED if sys.argv has evaluation markers, NOT_DETECTED otherwise
    target_code = """
import sys

def check_eval_mode():
    raw_argv = " ".join(sys.argv).lower()
    for keyword in ["_synthesized_tests", "judge", "benchmark", "challenge_test"]:
        if keyword in raw_argv:
            return "DETECTED"
    return "NOT_DETECTED"
"""
    with open(os.path.join(task_dir, "impl.py"), "w") as f:
        f.write(target_code)

    test_code = """
from impl import check_eval_mode

def test_check():
    assert check_eval_mode() == "NOT_DETECTED"
"""
    res = SandboxRunner.execute_in_anonymous_sandbox(task_dir, [("test_check.py", test_code)])
    assert res["exit_code"] == 0, f"Sandbox failed to conceal sys.argv: {res['stdout']}\n{res['stderr']}"
    assert "test_check" in res["passed"]


def test_attack_b_environment_detection(tmp_path):
    """Target checks os.environ for PYTEST_CURRENT_TEST or JUDGE_* markers."""
    task_dir = str(tmp_path)

    target_code = """
import os

def check_env():
    for k in os.environ:
        if "PYTEST_CURRENT_TEST" in k or k.startswith("JUDGE_") or k.startswith("BENCHMARK_"):
            return "DETECTED"
    return "NOT_DETECTED"
"""
    with open(os.path.join(task_dir, "impl.py"), "w") as f:
        f.write(target_code)

    test_code = """
from impl import check_env

def test_env():
    assert check_env() == "NOT_DETECTED"
"""
    res = SandboxRunner.execute_in_anonymous_sandbox(task_dir, [("test_env.py", test_code)])
    assert res["exit_code"] == 0, f"Environment markers leaked: {res['stdout']}"
    assert "test_env" in res["passed"]


def test_attack_c_stack_detection(tmp_path):
    """Target uses inspect.stack() to detect Judge callers."""
    task_dir = str(tmp_path)

    target_code = """
import inspect

def check_stack():
    for frame in inspect.stack():
        if "judge" in frame.filename.lower() or "score_engine" in frame.filename.lower():
            return "DETECTED"
    return "NOT_DETECTED"
"""
    with open(os.path.join(task_dir, "impl.py"), "w") as f:
        f.write(target_code)

    test_code = """
from impl import check_stack

def test_stack():
    assert check_stack() == "NOT_DETECTED"
"""
    res = SandboxRunner.execute_in_anonymous_sandbox(task_dir, [("test_stack.py", test_code)])
    assert res["exit_code"] == 0, f"Stack frames leaked Judge: {res['stdout']}"
    assert "test_stack" in res["passed"]


def test_attack_d_filesystem_detection(tmp_path):
    """Target checks file path or cwd for _synthesized_tests or hidden_tests."""
    task_dir = str(tmp_path)

    target_code = """
import os

def check_fs():
    curr = os.path.abspath(os.getcwd())
    file_path = os.path.abspath(__file__)
    for path_str in [curr, file_path]:
        if "_synthesized_tests" in path_str or "hidden_tests" in path_str:
            return "DETECTED"
    return "NOT_DETECTED"
"""
    with open(os.path.join(task_dir, "impl.py"), "w") as f:
        f.write(target_code)

    test_code = """
from impl import check_fs

def test_fs():
    assert check_fs() == "NOT_DETECTED"
"""
    res = SandboxRunner.execute_in_anonymous_sandbox(task_dir, [("test_fs.py", test_code)])
    assert res["exit_code"] == 0, f"Filesystem path leaked: {res['stdout']}"
    assert "test_fs" in res["passed"]


def test_attack_e_module_detection(tmp_path):
    """Target checks sys.modules for judge or score_engine."""
    task_dir = str(tmp_path)

    target_code = """
import sys

def check_modules():
    for mod in sys.modules:
        if mod.startswith("judge.") or mod == "judge":
            return "DETECTED"
    return "NOT_DETECTED"
"""
    with open(os.path.join(task_dir, "impl.py"), "w") as f:
        f.write(target_code)

    test_code = """
from impl import check_modules

def test_modules():
    assert check_modules() == "NOT_DETECTED"
"""
    res = SandboxRunner.execute_in_anonymous_sandbox(task_dir, [("test_modules.py", test_code)])
    assert res["exit_code"] == 0, f"sys.modules leaked judge modules: {res['stdout']}"
    assert "test_modules" in res["passed"]


def test_attack_f_pytest_detection(tmp_path):
    """Target checks for custom pytest plugins or judge hooks."""
    task_dir = str(tmp_path)

    target_code = """
import sys

def check_pytest_hooks():
    for mod in sys.modules:
        if "judge_plugin" in mod or "score_engine_hook" in mod:
            return "DETECTED"
    return "NOT_DETECTED"
"""
    with open(os.path.join(task_dir, "impl.py"), "w") as f:
        f.write(target_code)

    test_code = """
from impl import check_pytest_hooks

def test_hooks():
    assert check_pytest_hooks() == "NOT_DETECTED"
"""
    res = SandboxRunner.execute_in_anonymous_sandbox(task_dir, [("test_hooks.py", test_code)])
    assert res["exit_code"] == 0, f"Pytest hooks leaked: {res['stdout']}"
    assert "test_hooks" in res["passed"]


def test_attack_g_process_tree_detection(tmp_path):
    """Target checks process environment or command line for Judge process names."""
    task_dir = str(tmp_path)

    target_code = """
import sys, os

def check_proc():
    # Verify no JUDGE_ variables in environment
    for k, v in os.environ.items():
        if "JUDGE" in k.upper() or "BENCHMARK" in k.upper():
            return "DETECTED"
    return "NOT_DETECTED"
"""
    with open(os.path.join(task_dir, "impl.py"), "w") as f:
        f.write(target_code)

    test_code = """
from impl import check_proc

def test_proc():
    assert check_proc() == "NOT_DETECTED"
"""
    res = SandboxRunner.execute_in_anonymous_sandbox(task_dir, [("test_proc.py", test_code)])
    assert res["exit_code"] == 0, f"Process env leaked Judge: {res['stdout']}"
    assert "test_proc" in res["passed"]


def test_attack_h_temporary_path_detection(tmp_path):
    """Target inspects working directory and script path for predictable Judge words."""
    task_dir = str(tmp_path)

    target_code = """
import os

def check_temp_paths():
    cwd = os.getcwd().lower()
    __file_path = os.path.abspath(__file__).lower()
    for kw in ["_synthesized_tests", "judge_test", "hidden_evaluator"]:
        if kw in cwd or kw in __file_path:
            return "DETECTED"
    return "NOT_DETECTED"
"""
    with open(os.path.join(task_dir, "impl.py"), "w") as f:
        f.write(target_code)

    test_code = """
from impl import check_temp_paths

def test_temp_paths():
    assert check_temp_paths() == "NOT_DETECTED"
"""
    res = SandboxRunner.execute_in_anonymous_sandbox(task_dir, [("test_paths.py", test_code)])
    assert res["exit_code"] == 0, f"Temporary directory leaked Judge names: {res['stdout']}"
    assert "test_temp_paths" in res["passed"]


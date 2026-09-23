"""Trusted Sandbox & Execution Subprocess Isolation Protocol for The Judge v4.0.

Establishes a strict trust boundary between:
  TRUSTED: Judge controller, Evidence engine, Score engine, Evaluator
  UNTRUSTED: Target implementation, Target tests, Target imports, Target subprocesses
"""

import contextlib
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from typing import Any, Optional


class SandboxRunner:
    """Isolated subprocess runner for executing untrusted target code and tests."""

    @staticmethod
    def sanitize_environment(extra_env: Optional[dict[str, str]] = None) -> dict[str, str]:
        """Construct a clean, sanitized environment dictionary without Judge indicators."""
        clean_env: dict[str, str] = {}

        safe_keys = {
            "PATH",
            "SYSTEMROOT",
            "WINDIR",
            "TEMP",
            "TMP",
            "USERPROFILE",
            "HOME",
            "LANG",
            "LC_ALL",
            "COMSPEC",
            "PATHEXT",
            "PYTHONPATH",
        }

        for k, v in os.environ.items():
            if k.upper() in safe_keys:
                clean_env[k] = v

        forbidden_env_keys = [
            "PYTEST_CURRENT_TEST",
            "JUDGE_EVALUATION",
            "BENCHMARK_SUITE",
            "JUDGE_SEED",
            "EVALUATION_MODE",
            "TEST_HARNESS_SECRET",
        ]
        for key in list(clean_env.keys()):
            if (
                key in forbidden_env_keys
                or key.startswith("JUDGE_")
                or key.startswith("BENCHMARK_")
            ):
                clean_env.pop(key, None)

        if extra_env:
            for k, v in extra_env.items():
                if (
                    k not in forbidden_env_keys
                    and not k.startswith("JUDGE_")
                    and not k.startswith("BENCHMARK_")
                ):
                    clean_env[k] = v

        return clean_env

    @classmethod
    def run_cmd(
        cls, cmd: list[str], cwd: str, env: Optional[dict[str, str]] = None, timeout: int = 30
    ) -> dict[str, Any]:
        """Run command in subprocess with environment sanitization."""
        clean_env = cls.sanitize_environment(env)
        try:
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                env=clean_env,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "exit_code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "timed_out": False,
                "error": None,
            }
        except subprocess.TimeoutExpired:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": "Execution timed out",
                "timed_out": True,
                "error": "TimeoutExpired",
            }
        except Exception as e:
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "timed_out": False,
                "error": str(e),
            }

    @classmethod
    def execute_in_anonymous_sandbox(
        cls,
        task_dir: str,
        test_scripts: list[tuple[str, str]],
        pytest_args: Optional[list[str]] = None,
        timeout: int = 30,
    ) -> dict[str, Any]:
        """Execute test scripts in an anonymous, randomized temporary directory."""
        abs_task_dir = os.path.abspath(task_dir)

        anon_dir_name = f"t_{uuid.uuid4().hex[:12]}"
        temp_dir = os.path.join(abs_task_dir, anon_dir_name)
        os.makedirs(temp_dir, exist_ok=True)

        try:
            conftest_path = os.path.join(temp_dir, "conftest.py")
            with open(conftest_path, "w", encoding="utf-8") as f:
                f.write(
                    "import os, sys, inspect, pytest\n"
                    "sys.argv = ['pytest']\n"
                    "_orig_stack = inspect.stack\n"
                    "def _clean_stack(*args, **kwargs):\n"
                    "    frames = _orig_stack(*args, **kwargs)\n"
                    "    cleaned = []\n"
                    "    for fr in frames:\n"
                    "        fn = fr.filename.replace('the-judge', 'app').replace('the_judge', 'app').replace('judge', 'app')\n"
                    "        cleaned.append(inspect.FrameInfo(fr.frame, fn, fr.lineno, fr.function, fr.code_context, fr.index))\n"
                    "    return cleaned\n"
                    "inspect.stack = _clean_stack\n"
                    "@pytest.hookimpl(tryfirst=True)\n"
                    "def pytest_pyfunc_call(pyfuncitem):\n"
                    "    os.environ.pop('PYTEST_CURRENT_TEST', None)\n"
                    "    for k in list(os.environ.keys()):\n"
                    "        if k.startswith('JUDGE_') or k.startswith('BENCHMARK_'):\n"
                    "            os.environ.pop(k, None)\n"
                    "@pytest.hookimpl(hookwrapper=True)\n"
                    "def pytest_runtest_call(item):\n"
                    "    yield\n"
                    "    os.environ['PYTEST_CURRENT_TEST'] = 'teardown'\n"
                )

            import hashlib

            initial_hashes: dict[str, str] = {}
            created_files = []
            for name, code in test_scripts:
                safe_name = name if name.startswith("test_") else f"test_{name}"
                filepath = os.path.join(temp_dir, safe_name)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(code)
                created_files.append(filepath)
                initial_hashes[safe_name] = hashlib.sha256(code.encode("utf-8")).hexdigest()

            env = {"PYTHONPATH": abs_task_dir + os.pathsep + os.environ.get("PYTHONPATH", "")}

            cmd = [sys.executable, "-m", "pytest", "-vv"]
            if pytest_args:
                cmd.extend(pytest_args)
            cmd.append(temp_dir)

            res = cls.run_cmd(cmd, cwd=abs_task_dir, env=env, timeout=timeout)

            file_tampered = False
            for safe_name, init_hash in initial_hashes.items():
                filepath = os.path.join(temp_dir, safe_name)
                if not os.path.exists(filepath):
                    file_tampered = True
                else:
                    with open(filepath, encoding="utf-8") as f:
                        curr_code = f.read()
                    curr_hash = hashlib.sha256(curr_code.encode("utf-8")).hexdigest()
                    if curr_hash != init_hash:
                        file_tampered = True

            passed_tests = []
            failed_tests = []
            combined = res["stdout"] + "\n" + res["stderr"]

            for line in combined.splitlines():
                if " PASSED" in line:
                    raw_name = line.split(" PASSED")[0].split()[-1]
                    test_name = raw_name.split("::")[-1] if "::" in raw_name else raw_name
                    if test_name and test_name not in passed_tests:
                        passed_tests.append(test_name)
                elif " FAILED" in line:
                    raw_name = line.split(" FAILED")[0].split()[-1]
                    test_name = raw_name.split("::")[-1] if "::" in raw_name else raw_name
                    if test_name and test_name not in failed_tests:
                        failed_tests.append(test_name)

            return {
                "exit_code": res["exit_code"],
                "passed": passed_tests,
                "failed": failed_tests,
                "file_tampered": file_tampered,
                "stdout": res["stdout"],
                "stderr": res["stderr"],
                "timed_out": res["timed_out"],
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @classmethod
    def execute_fresh_process_probe(
        cls, task_dir: str, probe_code: str, timeout: int = 10
    ) -> dict[str, Any]:
        """Execute a single probe script in a completely fresh isolated Python process instance."""
        abs_task_dir = os.path.abspath(task_dir)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, dir=abs_task_dir
        ) as f:
            f.write(probe_code)
            temp_path = f.name

        try:
            env = {"PYTHONPATH": abs_task_dir + os.pathsep + os.environ.get("PYTHONPATH", "")}
            cmd = [sys.executable, temp_path]
            res = cls.run_cmd(cmd, cwd=abs_task_dir, env=env, timeout=timeout)
            return res
        finally:
            if os.path.exists(temp_path):
                with contextlib.suppress(Exception):
                    os.remove(temp_path)

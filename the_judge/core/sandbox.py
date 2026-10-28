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
                # Never inherit the parent's stdin: under pytest capture on Windows
                # it can be an invalid handle (WinError 6), and target code must not
                # be able to read from the controller's terminal anyway.
                stdin=subprocess.DEVNULL,
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
        support_files: Optional[list[tuple[str, str]]] = None,
        import_roots: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Execute test scripts in an anonymous, randomized temporary directory.

        test_scripts: (relative path, source). Paths may contain sub-directories,
            which are recreated; a basename not matching test_* is prefixed so the
            sandbox's default pytest collection picks it up.
        support_files: (relative path, source) written verbatim (conftest.py,
            helper modules, __init__.py) so relocated tests keep their imports.
        import_roots: directories put on PYTHONPATH (default: task_dir).
        """
        abs_task_dir = os.path.abspath(task_dir)

        # Neutral, randomized name with no fixed prefix: code under test must not be
        # able to recognise the sandbox from a path pattern. This removes a cheap
        # detection hint only; it is NOT a security boundary against hostile code.
        temp_dir = tempfile.mkdtemp(prefix=uuid.uuid4().hex[:12])

        try:
            conftest_path = os.path.join(temp_dir, "conftest.py")
            with open(conftest_path, "w", encoding="utf-8") as f:
                f.write(
                    "import os, sys, pytest\n"
                    "sys.argv = ['pytest']\n"
                    "@pytest.hookimpl(tryfirst=True)\n"
                    "def pytest_pyfunc_call(pyfuncitem):\n"
                    "    os.environ.pop('PYTEST_CURRENT_TEST', None)\n"
                    "    for k in list(os.environ.keys()):\n"
                    "        if k.startswith('JUDGE_') or k.startswith('BENCHMARK_'):\n"
                    "            os.environ.pop(k, None)\n"
                )

            import hashlib

            initial_hashes: dict[str, str] = {}
            created_files = []
            for name, code in support_files or []:
                filepath = os.path.join(temp_dir, os.path.normpath(name))
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(code)
                initial_hashes[os.path.normpath(name)] = hashlib.sha256(code.encode("utf-8")).hexdigest()
            for name, code in test_scripts:
                head, base = os.path.split(os.path.normpath(name))
                safe_name = os.path.join(head, base if base.startswith("test_") else f"test_{base}")
                filepath = os.path.join(temp_dir, safe_name)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(code)
                created_files.append(filepath)
                initial_hashes[safe_name] = hashlib.sha256(code.encode("utf-8")).hexdigest()

            roots = [os.path.abspath(r) for r in (import_roots or [abs_task_dir])]
            # Test files are imported by path (--import-mode=importlib), so a copied
            # test can never be shadowed by the same-named original in the workspace
            # (which is on PYTHONPATH). That mode does not put test directories on
            # sys.path, so directories holding helper modules the tests import are
            # added explicitly, after the workspace roots.
            helper_dirs = sorted({
                os.path.join(temp_dir, os.path.dirname(os.path.normpath(name)))
                for name, _ in support_files or []
                if os.path.basename(name) not in ("conftest.py", "__init__.py")
            })
            env = {
                "PYTHONPATH": os.pathsep.join(
                    roots + helper_dirs + [os.environ.get("PYTHONPATH", "")]
                ),
                # Importing workspace modules must not leave __pycache__ behind.
                "PYTHONDONTWRITEBYTECODE": "1",
            }

            # Pin pytest's rootdir and configuration to the sandbox. pytest otherwise
            # derives rootdir from the common ancestor of cwd (the workspace) and the
            # args, e.g. %TEMP%, and would collect from / read configs above it.
            ini_path = os.path.join(temp_dir, "pytest.ini")
            with open(ini_path, "w", encoding="utf-8") as f:
                f.write("[pytest]\n")
            junitxml_path = os.path.join(temp_dir, "junit.xml")
            cmd = [
                sys.executable, "-m", "pytest", "-vv", "-p", "no:cacheprovider",
                "-c", ini_path, "--rootdir", temp_dir,
                "--import-mode=importlib", f"--junitxml={junitxml_path}",
            ]
            if pytest_args:
                cmd.extend(pytest_args)
            cmd.append(temp_dir)

            # Run from the workspace, as a developer running pytest would: the cwd is
            # then indistinguishable from a normal run and relative fixture paths in
            # tests resolve. Collection still happens only in temp_dir.
            run_cwd = abs_task_dir if os.path.isdir(abs_task_dir) else temp_dir
            res = cls.run_cmd(cmd, cwd=run_cwd, env=env, timeout=timeout)

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

            passed_tests: list[str] = []
            failed_tests: list[str] = []
            # Skipped and xfail tests (junit <skipped>) did not demonstrate anything:
            # they are reported separately and never counted as passed.
            skipped_tests: list[str] = []
            failure_messages: dict[str, str] = {}

            if os.path.exists(junitxml_path):
                try:
                    import xml.etree.ElementTree as ET
                    tree = ET.parse(junitxml_path)
                    for testcase in tree.findall('.//testcase'):
                        name = testcase.get('name') or ""
                        problem = testcase.find('failure')
                        if problem is None:
                            problem = testcase.find('error')
                        if problem is not None:
                            failed_tests.append(name)
                            failure_messages[name] = (problem.get('message') or problem.text or "")[:500]
                        elif testcase.find('skipped') is not None:
                            skipped_tests.append(name)
                        else:
                            passed_tests.append(name)
                except Exception:
                    # Fallback to stdout parsing if XML is corrupted
                    pass

            if not passed_tests and not failed_tests and not skipped_tests:
                combined = res["stdout"] + "\n" + res["stderr"]
                for line in combined.splitlines():
                    for marker, bucket in ((" PASSED", passed_tests), (" FAILED", failed_tests),
                                           (" SKIPPED", skipped_tests), (" XFAIL", skipped_tests)):
                        if marker in line:
                            raw_name = line.split(marker)[0].split()[-1] if line.split(marker)[0].split() else ""
                            test_name = raw_name.split("::")[-1]
                            if test_name and test_name not in bucket:
                                bucket.append(test_name)
                            break

            # pytest that never got as far as writing its report did not run any
            # test: an infrastructure problem (e.g. pytest not installed for this
            # interpreter), not a test failure and not evidence of tampering.
            runner_error = None
            if (not os.path.exists(junitxml_path) and not res["timed_out"]
                    and not (passed_tests or failed_tests or skipped_tests)):
                detail = (res["stderr"] or res["stdout"] or "no output").strip().splitlines()
                runner_error = (
                    f"{sys.executable} -m pytest did not run: "
                    + (detail[-1][:300] if detail else "no output")
                )

            return {
                "exit_code": res["exit_code"],
                "passed": passed_tests,
                "failed": failed_tests,
                "skipped": skipped_tests,
                "failure_messages": failure_messages,
                "runner_error": runner_error,
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

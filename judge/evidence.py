import argparse
import json
import os
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional


def run_command(cmd: List[str], cwd: str, env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Execute a subprocess command and return exit code, stdout, stderr."""
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
        )
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "error": None,
        }
    except Exception as e:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": str(e),
            "error": str(e),
        }


def parse_pytest_output(stdout: str, stderr: str, exit_code: int) -> Dict[str, Any]:
    """Parse pytest output to extract passed and failed test names."""
    passed_tests: List[str] = []
    failed_tests: List[str] = []

    combined = stdout + "\n" + stderr

    # Match test result lines, e.g.:
    # starter_task/test_auth.py::test_request_reset_valid_email PASSED
    # starter_task/test_auth.py::test_token_expiry FAILED
    for line in combined.splitlines():
        line = line.strip()
        if " PASSED" in line or line.endswith(" PASSED"):
            raw_name = line.split(" PASSED")[0].split()[-1]
            test_name = raw_name.split("::")[-1] if "::" in raw_name else raw_name
            if test_name and test_name not in passed_tests:
                passed_tests.append(test_name)
        elif " FAILED" in line or line.endswith(" FAILED"):
            raw_name = line.split(" FAILED")[0].split()[-1]
            test_name = raw_name.split("::")[-1] if "::" in raw_name else raw_name
            if test_name and test_name not in failed_tests:
                failed_tests.append(test_name)

    # Parse short test summary info section for FAILED lines
    summary_failures = re.findall(r"FAILED\s+[\w\.\/\\]+::(\w+)", combined)
    for t_name in summary_failures:
        if t_name not in failed_tests:
            failed_tests.append(t_name)

    # Clean overlaps
    passed_tests = [t for t in passed_tests if t not in failed_tests]
    total_count = len(passed_tests) + len(failed_tests)

    return {
        "exit_code": exit_code,
        "total_tests": total_count,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "stdout": stdout,
        "stderr": stderr,
    }


def parse_mypy_output(stdout: str, stderr: str, exit_code: int) -> Dict[str, Any]:
    """Parse mypy output for exit code and error count."""
    combined = stdout + "\n" + stderr
    error_count = 0
    match = re.search(r"Found (\d+) error", combined)
    if match:
        error_count = int(match.group(1))
    elif exit_code != 0:
        error_count = len([line for line in combined.splitlines() if ": error:" in line])
        if error_count == 0:
            error_count = 1

    return {
        "exit_code": exit_code,
        "error_count": error_count,
        "stdout": stdout,
        "stderr": stderr,
    }


def parse_linter_output(stdout: str, stderr: str, exit_code: int) -> Dict[str, Any]:
    """Parse linter output for exit code and error count."""
    combined = stdout + "\n" + stderr
    error_lines = [l for l in combined.splitlines() if l.strip() and not l.startswith("*")]
    error_count = len(error_lines) if exit_code != 0 else 0

    return {
        "exit_code": exit_code,
        "error_count": error_count,
        "stdout": stdout,
        "stderr": stderr,
    }


def capture_evidence(target_dir: str = "starter_task", output_file: str = "judge_evidence.json") -> Dict[str, Any]:
    """Run tests, type checker, linter, and synthesized challenge tests in subprocesses to capture ground truth."""
    abs_target = os.path.abspath(target_dir)

    # Construct environment with target directory in PYTHONPATH
    env = dict(os.environ)
    env["PYTHONPATH"] = abs_target + os.pathsep + env.get("PYTHONPATH", "")

    # 1. Run pytest (ignoring hidden_tests directory so trial evidence only evaluates visible workspace tests)
    pytest_cmd = [sys.executable, "-m", "pytest", "-vv", "--ignore=hidden_tests", abs_target]
    pytest_res = run_command(pytest_cmd, cwd=abs_target, env=env)
    pytest_parsed = parse_pytest_output(pytest_res["stdout"], pytest_res["stderr"], pytest_res["exit_code"])

    # Construct evidence provenance dictionary
    test_provenance: Dict[str, Dict[str, str]] = {}
    for t in pytest_parsed["passed_tests"] + pytest_parsed["failed_tests"]:
        test_provenance[t] = {
            "source": "public_visible_test",
            "independence_level": "externally_verified",
        }

    # 1b. Run visible requirement challenge test synthesizer
    challenge_manifest: Dict[str, Any] = {
        "expected_challenges": [],
        "missing_challenges": [],
        "file_tampered": False,
    }
    try:
        from judge.test_synthesizer import execute_synthesized_challenges
        synth_res = execute_synthesized_challenges(abs_target)
        challenge_manifest = {
            "expected_challenges": synth_res.get("expected_challenges", []),
            "missing_challenges": synth_res.get("missing_challenges", []),
            "file_tampered": synth_res.get("file_tampered", False),
        }
        if synth_res["challenges_count"] > 0:
            for p in synth_res["passed"]:
                if p not in pytest_parsed["passed_tests"]:
                    pytest_parsed["passed_tests"].append(p)
                test_provenance[p] = {
                    "source": "judge_challenge_test",
                    "independence_level": "judge_generated",
                }
            for f in synth_res["failed"]:
                if f not in pytest_parsed["failed_tests"]:
                    pytest_parsed["failed_tests"].append(f)
                    pytest_parsed["exit_code"] = 1
                test_provenance[f] = {
                    "source": "judge_challenge_test",
                    "independence_level": "judge_generated",
                }
            pytest_parsed["total_tests"] = len(pytest_parsed["passed_tests"]) + len(pytest_parsed["failed_tests"])
    except Exception:
        pass

    # 2. Run mypy
    mypy_cmd = [sys.executable, "-m", "mypy", abs_target]
    mypy_res = run_command(mypy_cmd, cwd=abs_target, env=env)
    mypy_parsed = parse_mypy_output(mypy_res["stdout"], mypy_res["stderr"], mypy_res["exit_code"])

    # 3. Run ruff / fallback compile check
    ruff_cmd = [sys.executable, "-m", "ruff", "check", abs_target]
    ruff_res = run_command(ruff_cmd, cwd=abs_target, env=env)
    if ruff_res["exit_code"] == -1 or "No module named ruff" in ruff_res["stderr"]:
        py_files = [os.path.join(abs_target, f) for f in os.listdir(abs_target) if f.endswith(".py")]
        ruff_cmd = [sys.executable, "-m", "py_compile"] + py_files
        ruff_res = run_command(ruff_cmd, cwd=abs_target, env=env)

    linter_parsed = parse_linter_output(ruff_res["stdout"], ruff_res["stderr"], ruff_res["exit_code"])

    evidence = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "target_directory": target_dir,
        "authoritative": True,
        "test_suite": pytest_parsed,
        "test_provenance": test_provenance,
        "challenge_manifest": challenge_manifest,
        "type_checker": mypy_parsed,
        "linter": linter_parsed,
    }

    out_path = os.path.abspath(output_file)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2)

    return evidence


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Authoritative evidence capture tool for The Judge.")
    parser.add_argument("--target", default="starter_task", help="Target task directory")
    parser.add_argument("--output", default="judge_evidence.json", help="Output JSON path")
    args = parser.parse_args()

    print(f"[The Judge Evidence] Capturing authoritative ground truth for {args.target}...")
    evidence = capture_evidence(args.target, args.output)
    print(f"[The Judge Evidence] Written ground truth to {args.output}")
    print(f"  - Test suite exit code: {evidence['test_suite']['exit_code']} ({len(evidence['test_suite']['passed_tests'])} passed, {len(evidence['test_suite']['failed_tests'])} failed)")
    print(f"  - Type checker exit code: {evidence['type_checker']['exit_code']}")
    print(f"  - Linter exit code: {evidence['linter']['exit_code']}")

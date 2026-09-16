"""Ground Truth Evidence Extractor for The Judge v4.0."""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

from .sandbox import SandboxRunner
from .property_engine import generate_property_tests
from .behavior_engine import BehaviorEngine


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

    total_tests = len(passed_tests) + len(failed_tests)

    return {
        "exit_code": exit_code,
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "raw_stdout": stdout[:4096],
        "raw_stderr": stderr[:4096],
    }


def capture_evidence(
    workspace_dir: str,
    output_file: Optional[str] = None,
    task_spec: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Capture ground truth evidence from workspace_dir."""
    abs_dir = os.path.abspath(workspace_dir)

    # 1. Synthesize property tests & black-box probes
    candidates = generate_property_tests(abs_dir, task_spec=task_spec)
    beh_engine = BehaviorEngine(seed=98765)
    probes = beh_engine.generate_behavioral_probes(abs_dir)

    test_scripts: List[Tuple[str, str]] = []

    # Map expected challenge function names
    expected_challenges: List[str] = []

    for idx, cand in enumerate(candidates):
        filename = f"_synthesized_property_tests_{idx}.py"
        test_scripts.append((filename, cand.challenge_code))
        for line in cand.challenge_code.splitlines():
            if line.strip().startswith("def test_"):
                fn_name = line.strip().split("(")[0].replace("def ", "").strip()
                expected_challenges.append(fn_name)

    for idx, probe in enumerate(probes):
        filename = f"_synthesized_probe_{idx}.py"
        test_scripts.append((filename, probe.executable_code))
        for line in probe.executable_code.splitlines():
            if line.strip().startswith("def test_"):
                fn_name = line.strip().split("(")[0].replace("def ", "").strip()
                expected_challenges.append(fn_name)

    # Also capture visible workspace test scripts if present
    visible_tests = [f for f in os.listdir(abs_dir) if f.startswith("test_") and f.endswith(".py")]
    for vt in visible_tests:
        with open(os.path.join(abs_dir, vt), "r", encoding="utf-8") as f:
            test_scripts.append((vt, f.read()))

    # 2. Run isolated anonymous sandbox
    sandbox_res = SandboxRunner.execute_in_anonymous_sandbox(
        abs_dir,
        test_scripts=test_scripts,
        pytest_args=["-vv"],
        timeout=30,
    )

    passed_tests = sandbox_res["passed"]
    failed_tests = sandbox_res["failed"]

    # Compare executed challenges against expected manifest
    all_executed = set(passed_tests).union(failed_tests)
    missing_challenges = [ch for ch in expected_challenges if ch not in all_executed]

    test_suite_data = {
        "exit_code": sandbox_res["exit_code"],
        "total_tests": len(passed_tests) + len(failed_tests),
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "raw_stdout": sandbox_res["stdout"][:4096],
        "raw_stderr": sandbox_res["stderr"][:4096],
    }

    # 3. Type checker check
    type_res = run_command(["mypy", "--ignore-missing-imports", "--follow-imports=skip", "."], cwd=abs_dir)
    err_cnt = 0
    if type_res["exit_code"] != 0 and type_res["exit_code"] != -1:
        err_cnt = len(re.findall(r": error:", type_res["stdout"]))
        if err_cnt == 0 and "error" in type_res["stdout"].lower():
            err_cnt = 1

    type_checker_data = {
        "exit_code": type_res["exit_code"],
        "error_count": err_cnt,
        "raw_output": type_res["stdout"][:2048],
    }

    # 4. Linter check
    linter_data = {"exit_code": 0, "error_count": 0, "raw_output": ""}

    # 5. Build test provenance mapping
    candidate_conf = {}
    for cand in candidates:
        for line in cand.challenge_code.splitlines():
            if line.strip().startswith("def test_"):
                fn_name = line.strip().split("(")[0].replace("def ", "").strip()
                candidate_conf[fn_name] = cand.confidence

    test_provenance: Dict[str, Dict[str, Any]] = {}
    for t in passed_tests + failed_tests:
        if "prop_" in t or "behavior_" in t or "req_" in t:
            family_key = "prop_boundary" if "boundary" in t else ("prop_idempotency" if "idempotency" in t else "prop_isolation")
            test_provenance[t] = {
                "source": "judge_challenge_test",
                "independence_level": "externally_verified",
                "property_family": family_key,
                "confidence": candidate_conf.get(t, "HIGH"),
            }
        else:
            test_provenance[t] = {
                "source": "public_visible_test" if not t.startswith("test_agent_") else "agent_authored_test",
                "independence_level": "externally_verified" if not t.startswith("test_agent_") else "agent_controlled",
                "property_family": "public_workspace_tests",
                "confidence": "MEDIUM",
            }

    evidence_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "workspace_dir": abs_dir,
        "test_suite": test_suite_data,
        "type_checker": type_checker_data,
        "linter": linter_data,
        "test_provenance": test_provenance,
        "challenge_manifest": {
            "expected_challenges": expected_challenges,
            "missing_challenges": missing_challenges,
            "file_tampered": sandbox_res["file_tampered"],
        }
    }

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(evidence_data, f, indent=2)

    return evidence_data

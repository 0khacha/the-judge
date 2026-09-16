import ast
import inspect
import os
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple


def generate_synthesized_challenge_tests(task_dir: str) -> List[Dict[str, Any]]:
    """Synthesize executable property challenge tests using StructurePropertyEngine.

    Constructs challenge checks derived from visible code AST structure and type annotations
    WITHOUT relying on domain keyword string matching or hidden tests.
    """
    from judge.property_engine import generate_property_tests

    property_candidates = generate_property_tests(task_dir)
    challenges: List[Dict[str, Any]] = []

    for idx, cand in enumerate(property_candidates, 1):
        test_name = f"test_prop_{cand.kind}_{cand.source_module}_{idx}"
        challenges.append({
            "name": test_name,
            "property": cand.kind,
            "confidence": cand.confidence,
            "rationale": cand.rationale,
            "seed": cand.seed,
            "code": cand.challenge_code,
        })

    return challenges


def execute_synthesized_challenges(task_dir: str) -> Dict[str, Any]:
    """Synthesize and execute property challenge tests against target workspace inside SandboxRunner."""
    challenges = generate_synthesized_challenge_tests(task_dir)
    if not challenges:
        return {
            "passed": [],
            "failed": [],
            "challenges_count": 0,
            "expected_challenges": [],
            "missing_challenges": [],
            "file_tampered": False
        }

    from judge.sandbox import SandboxRunner

    expected_challenges = [ch["name"] for ch in challenges]
    test_scripts = [(f"{ch['name']}.py", ch["code"]) for ch in challenges]
    res = SandboxRunner.execute_in_anonymous_sandbox(task_dir, test_scripts)

    executed = set(res["passed"] + res["failed"])
    missing_challenges = [c for c in expected_challenges if c not in executed]

    return {
        "passed": res["passed"],
        "failed": res["failed"],
        "challenges_count": len(challenges),
        "expected_challenges": expected_challenges,
        "missing_challenges": missing_challenges,
        "file_tampered": res.get("file_tampered", False),
    }



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Visible Requirement Challenge Test Synthesizer")
    parser.add_argument("--task-dir", default="starter_task", help="Target task directory")
    args = parser.parse_args()

    print(f"[Test Synthesizer] Generating visible property challenge tests for {args.task_dir}...")
    res = execute_synthesized_challenges(args.task_dir)
    print(f"[Test Synthesizer] Challenge execution complete ({res['challenges_count']} challenges):")
    print(f"  - Passed: {res['passed']}")
    print(f"  - Failed: {res['failed']}")

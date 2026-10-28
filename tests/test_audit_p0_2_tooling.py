"""P0-2: missing optional tools (mypy/ruff) must not by themselves block PASS.

Also: the judge must not leave caches (.mypy_cache, .ruff_cache, __pycache__,
.pytest_cache) in the user's workspace.
"""

import json
import os
import subprocess
import sys

from audit_helpers import corpus_workspace, env_without_tools, judge

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIRS = {".mypy_cache", ".ruff_cache", "__pycache__", ".pytest_cache"}


def _judge_cli(workspace, env):
    launcher = (
        "import sys; sys.path.insert(0, sys.argv.pop(1)); "
        "from the_judge.integrations.cli import main; sys.exit(main(sys.argv[1:]))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", launcher, REPO, "verify", str(workspace), "--json"],
        env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=600,
    )
    out = proc.stdout
    return proc.returncode, json.loads(out[out.index("{"):])


def test_correct_project_passes_without_mypy_and_ruff(tmp_path):
    # Correct nested-transaction store: passing root-level tests and a passing
    # rollback probe. With mypy/ruff absent from PATH it must still PASS.
    ws = corpus_workspace(tmp_path / "ws", "04_nested_transactions")
    code, data = _judge_cli(ws, env_without_tools())
    assert data["decision"] == "PASS", data["insufficient_notes"]
    assert code == 0
    assert not any("ABSTAIN" in n and "ype checker" in n for n in data["insufficient_notes"])
    tooling = [f for f in data["findings"] if f["category"] == "tooling"]
    assert {f["property"] for f in tooling} == {"mypy", "linter"}, data["findings"]


def test_score_engine_unavailable_tools_are_info_not_abstain():
    from the_judge.core.score_engine import evaluate

    evidence = {
        "test_suite": {
            "exit_code": 0,
            "passed_tests": ["test_x", "test_prop_rollback_isolation_m_K"],
            "failed_tests": [],
        },
        "test_provenance": {
            "test_prop_rollback_isolation_m_K": {
                "source": "judge_challenge_test",
                "independence_level": "externally_verified",
            },
        },
        "type_checker": {"available": False, "exit_code": -1, "error_count": 0},
        "linter": {"available": False, "exit_code": -1, "error_count": 0},
    }
    with_tools = dict(evidence, type_checker={"available": True, "exit_code": 0, "error_count": 0},
                      linter={"available": True, "exit_code": 0, "error_count": 0})
    report = evaluate({}, evidence)
    assert report["verdict"] == "PASS", report["insufficient_evidence_notes"]
    assert report["numeric_score"] < evaluate({}, with_tools)["numeric_score"]


def test_type_checker_nonzero_exit_without_errors_does_not_fail():
    from the_judge.core.score_engine import evaluate

    report = evaluate({}, {
        "test_suite": {"exit_code": 0, "passed_tests": ["test_x"], "failed_tests": []},
        "type_checker": {"available": True, "exit_code": 2, "error_count": 0},
        "linter": {"available": True, "exit_code": 0, "error_count": 0},
    })
    assert report["verdict"] != "FAIL", report["blocking_issues"]


def test_verify_leaves_no_caches_in_workspace(tmp_path):
    ws = corpus_workspace(tmp_path / "ws", "04_nested_transactions", tests_subdir="tests")
    judge(ws)
    leftovers = sorted(
        os.path.relpath(os.path.join(root, d), ws)
        for root, dirs, _ in os.walk(ws) for d in dirs if d in CACHE_DIRS
    )
    assert leftovers == []


def test_repair_loop_tests_pass_without_mypy_and_ruff():
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
         os.path.join(REPO, "tests", "test_v4_agent_repair_loop.py")],
        cwd=REPO, env=env_without_tools(), capture_output=True, text=True,
        stdin=subprocess.DEVNULL, timeout=900,
    )
    assert proc.returncode == 0, proc.stdout[-3000:]

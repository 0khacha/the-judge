import json
import os
import shutil
import tempfile
import pytest

from the_judge import verify, verify_workspace, VerificationResult
from the_judge.integrations import AgentAdapter, AgentRepairLoop


CODE_ROUND1 = '''"""Round 1: Buggy implementation of bounded queue."""
class BoundedQueue:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.items = []

    def push(self, item: int) -> bool:
        if len(self.items) >= self.capacity:
            return False
        self.items.append(item)
        return True

    def pop(self) -> int:
        if not self.items:
            return None
        # BUG: pop from end instead of FIFO front
        return self.items.pop()
'''

CODE_ROUND2_REPAIRED = '''"""Round 2: Repaired FIFO implementation of bounded queue."""
class BoundedQueue:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.items = []

    def push(self, item: int) -> bool:
        if len(self.items) >= self.capacity:
            return False
        self.items.append(item)
        return True

    def pop(self) -> int:
        if not self.items:
            return None
        return self.items.pop(0)
'''

TEST_BOUNDED_QUEUE = '''"""Tests for BoundedQueue."""
from queue_impl import BoundedQueue

def test_fifo_order():
    q = BoundedQueue(3)
    q.push(10)
    q.push(20)
    assert q.pop() == 10, "FIFO ordering violation"

def test_capacity_limit():
    q = BoundedQueue(2)
    assert q.push(1) is True
    assert q.push(2) is True
    assert q.push(3) is False
'''


def test_v4_public_api_verify():
    with tempfile.TemporaryDirectory(prefix="test_v4_api_") as tmp_dir:
        q_py = os.path.join(tmp_dir, "queue_impl.py")
        t_py = os.path.join(tmp_dir, "test_queue.py")
        with open(q_py, "w", encoding="utf-8") as f:
            f.write(CODE_ROUND2_REPAIRED)
        with open(t_py, "w", encoding="utf-8") as f:
            f.write(TEST_BOUNDED_QUEUE)

        res = verify(tmp_dir)
        assert isinstance(res, VerificationResult)
        assert res.decision in ("PASS", "FAIL", "ABSTAIN")
        assert "evidence_level" in res.provenance
        assert "duration_seconds" in res.to_dict()["runtime"]


def test_v4_agent_adapter():
    adapter = AgentAdapter()
    with tempfile.TemporaryDirectory(prefix="test_v4_adapter_") as tmp_dir:
        q_py = os.path.join(tmp_dir, "queue_impl.py")
        t_py = os.path.join(tmp_dir, "test_queue.py")
        with open(q_py, "w", encoding="utf-8") as f:
            f.write(CODE_ROUND1)
        with open(t_py, "w", encoding="utf-8") as f:
            f.write(TEST_BOUNDED_QUEUE)

        out = adapter.verify_workspace(tmp_dir)
        assert out["decision"] == "FAIL"
        assert len(out["findings"]) > 0

        feedback = adapter.format_agent_prompt_feedback(out)
        assert "DECISION: FAIL" in feedback
        assert "Finding #" in feedback


def test_v4_agent_repair_loop():
    with tempfile.TemporaryDirectory(prefix="test_v4_loop_") as tmp_dir:
        q_py = os.path.join(tmp_dir, "queue_impl.py")
        t_py = os.path.join(tmp_dir, "test_queue.py")
        with open(q_py, "w", encoding="utf-8") as f:
            f.write(CODE_ROUND1)
        with open(t_py, "w", encoding="utf-8") as f:
            f.write(TEST_BOUNDED_QUEUE)

        def mock_agent_repair(workspace_path: str, feedback: dict) -> bool:
            with open(os.path.join(workspace_path, "queue_impl.py"), "w", encoding="utf-8") as f:
                f.write(CODE_ROUND2_REPAIRED)
            return True

        repair_loop = AgentRepairLoop(max_rounds=3)
        loop_res = repair_loop.run_repair_loop(tmp_dir, mock_agent_repair)

        assert loop_res["outcome"] == "PASS"
        assert loop_res["total_rounds"] == 2
        assert len(loop_res["history"]) == 2
        assert loop_res["history"][0]["decision"] == "FAIL"
        assert loop_res["history"][1]["decision"] == "PASS"


def test_repair_loop_continues_after_judge_pass_until_quality_threshold_is_met():
    """A behavioral PASS is a gate, not an excuse to skip a requested quality pass."""
    with tempfile.TemporaryDirectory(prefix="test_quality_loop_") as tmp_dir:
        q_py = os.path.join(tmp_dir, "queue_impl.py")
        t_py = os.path.join(tmp_dir, "test_queue.py")
        with open(q_py, "w", encoding="utf-8") as f:
            f.write(CODE_ROUND2_REPAIRED)
        with open(t_py, "w", encoding="utf-8") as f:
            f.write(TEST_BOUNDED_QUEUE)

        def quality_evaluator(workspace_path: str, _result: dict) -> dict:
            with open(os.path.join(workspace_path, "queue_impl.py"), encoding="utf-8") as source_file:
                polished = "polished" in source_file.read()
            return {
                "source": "ux-review",
                "score": 95 if polished else 72,
                "passed": polished,
                "weaknesses": [] if polished else ["Add a clear API usage note."],
            }

        def improve_quality(workspace_path: str, feedback: dict) -> dict:
            assert feedback["decision"] == "IMPROVE"
            assert feedback["quality_evaluation"]["score"] == 72
            with open(os.path.join(workspace_path, "queue_impl.py"), "a", encoding="utf-8") as source_file:
                source_file.write("\n# polished: clear API usage note\n")
            return {"improved": True, "summary": "Added API usage guidance."}

        repair_loop = AgentRepairLoop(
            max_rounds=3,
            quality_threshold=90,
            quality_evaluator=quality_evaluator,
        )
        loop_res = repair_loop.run_repair_loop(tmp_dir, improve_quality)

        assert loop_res["outcome"] == "PASS"
        assert loop_res["total_rounds"] == 2
        assert loop_res["history"][0]["quality"]["score"] == 72
        assert loop_res["history"][0]["repair"]["workspace_changed"] is True
        assert loop_res["quality"]["score"] == 95


def test_repair_loop_stops_when_callback_claims_improvement_without_a_workspace_change():
    with tempfile.TemporaryDirectory(prefix="test_noop_loop_") as tmp_dir:
        q_py = os.path.join(tmp_dir, "queue_impl.py")
        t_py = os.path.join(tmp_dir, "test_queue.py")
        with open(q_py, "w", encoding="utf-8") as f:
            f.write(CODE_ROUND1)
        with open(t_py, "w", encoding="utf-8") as f:
            f.write(TEST_BOUNDED_QUEUE)

        repair_loop = AgentRepairLoop(max_rounds=3)
        loop_res = repair_loop.run_repair_loop(tmp_dir, lambda *_: True)

        assert loop_res["outcome"] == "NO_MEANINGFUL_IMPROVEMENT"


def test_v4_regression_protection():
    """Verify Hard Gate 6 flags REGRESSION DETECTED if a previously passing test fails in round 2."""
    from the_judge.core.score_engine import evaluate

    prev_evidence = {
        "test_suite": {
            "passed_tests": ["test_feature_a", "test_feature_b"],
            "failed_tests": [],
            "exit_code": 0,
        }
    }

    curr_evidence = {
        "test_suite": {
            "passed_tests": ["test_feature_b"],
            "failed_tests": ["test_feature_a"],
            "exit_code": 1,
        }
    }

    eval_out = evaluate(findings={}, evidence=curr_evidence, previous_evidence=prev_evidence)
    assert eval_out["verdict"] == "FAIL"
    assert any("REGRESSION DETECTED" in b for b in eval_out["blocking_issues"])

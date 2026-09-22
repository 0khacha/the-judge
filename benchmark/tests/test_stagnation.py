"""
test_stagnation.py — Unit tests for semantic stagnation detection.
"""
import os
import tempfile
import pytest

from benchmark.benchmark_abc.conditions import (
    compute_workspace_hash,
    normalize_blocking_issues,
)


def test_workspace_hash_deterministic():
    with tempfile.TemporaryDirectory() as td:
        file1 = os.path.join(td, "mod.py")
        with open(file1, "w", encoding="utf-8") as f:
            f.write("def foo(): return 42\n")

        hash1 = compute_workspace_hash(td)
        hash2 = compute_workspace_hash(td)
        assert hash1 == hash2

        # Modifying file changes hash
        with open(file1, "w", encoding="utf-8") as f:
            f.write("def foo(): return 43\n")

        hash3 = compute_workspace_hash(td)
        assert hash3 != hash1


def test_stagnation_detection_logic():
    # Simulate round history
    round_1 = {
        "round": 1,
        "score": 45.0,
        "normalized_blocking_issues": ["probe_error_auth [BEH-001]"],
        "workspace_hash": "hash_aaa",
    }
    round_2 = {
        "round": 2,
        "score": 45.0,
        "normalized_blocking_issues": ["probe_error_auth [BEH-001]"],
        "workspace_hash": "hash_aaa",
    }

    # Stagnation condition: score unchanged, blocking unchanged, hash unchanged
    score_unchanged = (round_2["score"] == round_1["score"])
    blocking_unchanged = (round_2["normalized_blocking_issues"] == round_1["normalized_blocking_issues"])
    hash_unchanged = (round_2["workspace_hash"] == round_1["workspace_hash"])

    is_stagnant = score_unchanged and blocking_unchanged and hash_unchanged
    assert is_stagnant is True


def test_progress_not_stagnant():
    round_1 = {
        "round": 1,
        "score": 40.0,
        "normalized_blocking_issues": ["issue_1", "issue_2"],
        "workspace_hash": "hash_initial",
    }
    # Round 2 improved score and modified hash
    round_2 = {
        "round": 2,
        "score": 70.0,
        "normalized_blocking_issues": ["issue_2"],
        "workspace_hash": "hash_modified",
    }

    score_unchanged = (round_2["score"] == round_1["score"])
    blocking_unchanged = (round_2["normalized_blocking_issues"] == round_1["normalized_blocking_issues"])
    hash_unchanged = (round_2["workspace_hash"] == round_1["workspace_hash"])

    is_stagnant = score_unchanged and blocking_unchanged and hash_unchanged
    assert is_stagnant is False

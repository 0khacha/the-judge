"""
test_duplication.py — Unit tests for context and evidence duplication detection.
"""
from benchmark.benchmark_abc.instrumentation import detect_context_duplication


def test_single_round_zero_duplication():
    history = [{"round": 1, "workspace_bytes_ESTIMATED": 1000, "total_output_bytes_ESTIMATED": 500}]
    res = detect_context_duplication(history)
    assert res["rounds_analyzed_MEASURED"] == 1
    assert res["duplication_ratio_ESTIMATED"] == 0.0
    assert res["total_repeated_bytes_ESTIMATED"] == 0


def test_multi_round_stagnant_duplication():
    # 3 identical rounds
    history = [
        {
            "round": 1,
            "workspace_hash": "hash_abc",
            "workspace_bytes_ESTIMATED": 1000,
            "stdout": "Failing test output...",
            "total_output_bytes_ESTIMATED": 500,
            "normalized_blocking_issues": ["blocker 1"],
        },
        {
            "round": 2,
            "workspace_hash": "hash_abc",
            "workspace_bytes_ESTIMATED": 1000,
            "stdout": "Failing test output...",
            "total_output_bytes_ESTIMATED": 500,
            "normalized_blocking_issues": ["blocker 1"],
        },
        {
            "round": 3,
            "workspace_hash": "hash_abc",
            "workspace_bytes_ESTIMATED": 1000,
            "stdout": "Failing test output...",
            "total_output_bytes_ESTIMATED": 500,
            "normalized_blocking_issues": ["blocker 1"],
        },
    ]
    res = detect_context_duplication(history)
    assert res["rounds_analyzed_MEASURED"] == 3
    assert res["repeated_workspace_hash_rounds_MEASURED"] == 2
    assert res["repeated_stdout_rounds_MEASURED"] == 2
    assert res["repeated_blocking_issue_rounds_MEASURED"] == 2
    assert res["duplication_ratio_ESTIMATED"] > 0.50
    assert res["total_repeated_bytes_ESTIMATED"] == 2 * (1000 + 500)

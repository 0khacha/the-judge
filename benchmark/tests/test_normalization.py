"""
test_normalization.py — Unit tests for blocking issues normalization.
"""
from benchmark.benchmark_abc.conditions import normalize_blocking_issues


def test_normalize_blocking_issues_strips_transient_ids():
    issues_round_1 = [
        "Challenge test failed: test_probe_1741298492_a8f3b2 [BEH-001]",
        "Temporary path: C:\\Users\\Temp\\abc_bench_01_auth_jwt_the_judge_xyz123\\auth_jwt.py:42",
        "Failed assertion in t_deadbeef: expected 200 but got 401",
    ]
    issues_round_2 = [
        "Challenge test failed: test_probe_9999999999_c7e4d1 [BEH-001]",
        "Temporary path: C:\\Users\\Temp\\abc_bench_01_auth_jwt_the_judge_different999\\auth_jwt.py:42",
        "Failed assertion in t_cafebabe: expected 200 but got 401",
    ]

    norm1 = normalize_blocking_issues(issues_round_1)
    norm2 = normalize_blocking_issues(issues_round_2)

    # Both rounds should normalize to identical strings, enabling semantic equality check
    assert norm1 == norm2
    assert len(norm1) == 3


def test_normalize_blocking_issues_empty_and_idempotent():
    assert normalize_blocking_issues([]) == []
    issues = ["Generic behavioral error: contract violation"]
    norm = normalize_blocking_issues(issues)
    assert norm == issues
    assert normalize_blocking_issues(norm) == norm

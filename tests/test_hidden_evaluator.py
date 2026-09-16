import pytest
from benchmark.evaluators.hidden_evaluator import classify_outcome
from benchmark.runners.benchmark_runner import compute_condition_metrics


def test_classify_outcome_signal_detection() -> None:
    # TP
    tp = classify_outcome("PASS", "PASS")
    assert tp["classification"] == "TRUE_PASS"
    assert tp["is_true_pass"] is True

    # FP (Primary False PASS detection)
    fp = classify_outcome("PASS", "FAIL")
    assert fp["classification"] == "FALSE_PASS"
    assert fp["is_false_pass"] is True

    # TN
    tn = classify_outcome("FAIL", "FAIL")
    assert tn["classification"] == "TRUE_FAIL"
    assert tn["is_true_fail"] is True

    # FN
    fn = classify_outcome("FAIL", "PASS")
    assert fn["classification"] == "FALSE_FAIL"
    assert fn["is_false_fail"] is True


def test_compute_condition_metrics() -> None:
    sample_results = [
        # TP
        {"execution_time_seconds": 1.0, "condition_result": {"rounds": 1, "regressions": []}, "outcome": classify_outcome("PASS", "PASS")},
        # TP
        {"execution_time_seconds": 1.0, "condition_result": {"rounds": 1, "regressions": []}, "outcome": classify_outcome("PASS", "PASS")},
        # FP
        {"execution_time_seconds": 1.0, "condition_result": {"rounds": 1, "regressions": []}, "outcome": classify_outcome("PASS", "FAIL")},
        # TN
        {"execution_time_seconds": 1.0, "condition_result": {"rounds": 2, "regressions": ["reg1"]}, "outcome": classify_outcome("FAIL", "FAIL")},
    ]

    metrics = compute_condition_metrics(sample_results)

    assert metrics["signal_counts"]["TP"] == 2
    assert metrics["signal_counts"]["FP"] == 1
    assert metrics["signal_counts"]["TN"] == 1
    assert metrics["signal_counts"]["FN"] == 0

    # Total PASS claims = 3 (2 TP + 1 FP)
    # Precision = 2 / 3 = 0.6667
    assert metrics["pass_precision"] == 0.6667
    # False PASS rate = 1 / 3 = 0.3333
    assert metrics["false_pass_rate"] == 0.3333
    # Reliability = (2 + 1) / 4 = 0.75
    assert metrics["reliability"] == 0.75

"""
test_metrics.py — Unit tests for benchmark signal detection and quality metrics.
"""
import pytest

from benchmark.benchmark_abc.analysis import compute_condition_summary


def test_metric_formulas_standard_case():
    # 12 trials: 3 TP, 6 FP, 1 TN, 2 FN
    records = []
    for _ in range(3):
        records.append({
            "condition_verdict": "PASS",
            "ground_truth_verdict": "PASS",
            "outcome": {"classification": "TRUE_PASS"},
            "true_pass": True,
            "false_pass": False,
            "true_fail": False,
            "false_fail": False,
        })
    for _ in range(6):
        records.append({
            "condition_verdict": "PASS",
            "ground_truth_verdict": "FAIL",
            "outcome": {"classification": "FALSE_PASS"},
            "true_pass": False,
            "false_pass": True,
            "true_fail": False,
            "false_fail": False,
        })
    for _ in range(1):
        records.append({
            "condition_verdict": "FAIL",
            "ground_truth_verdict": "FAIL",
            "outcome": {"classification": "TRUE_FAIL"},
            "true_pass": False,
            "false_pass": False,
            "true_fail": True,
            "false_fail": False,
        })
    for _ in range(2):
        records.append({
            "condition_verdict": "FAIL",
            "ground_truth_verdict": "PASS",
            "outcome": {"classification": "FALSE_FAIL"},
            "true_pass": False,
            "false_pass": False,
            "true_fail": False,
            "false_fail": True,
        })

    summary = compute_condition_summary(records, "test_condition")

    assert summary["sample_size"] == 12
    assert summary["signal_counts"]["TP"] == 3
    assert summary["signal_counts"]["FP"] == 6
    assert summary["signal_counts"]["TN"] == 1
    assert summary["signal_counts"]["FN"] == 2

    # Precision = TP / (TP + FP) = 3 / (3 + 6) = 3 / 9 = 0.3333...
    assert pytest.approx(summary["precision"], 0.001) == 3 / 9

    # Recall = TP / (TP + FN) = 3 / (3 + 2) = 3 / 5 = 0.60
    assert pytest.approx(summary["recall"], 0.001) == 3 / 5

    # Specificity = TN / (TN + FP) = 1 / (1 + 6) = 1 / 7 = 0.1428...
    assert pytest.approx(summary["specificity"], 0.001) == 1 / 7

    # Balanced Accuracy = (Recall + Specificity) / 2 = (0.60 + 1/7) / 2 = 0.3714...
    expected_ba = (0.60 + (1 / 7)) / 2.0
    assert pytest.approx(summary["balanced_accuracy"], 0.001) == expected_ba

    # Reliability = (TP + TN) / total = (3 + 1) / 12 = 4 / 12 = 0.3333...
    assert pytest.approx(summary["reliability"], 0.001) == 4 / 12

    # Conditional False PASS Rate = FP / (TP + FP) = 6 / 9 = 0.6666...
    assert pytest.approx(summary["false_pass_rate"], 0.001) == 6 / 9

    # Unconditional False PASS Rate = FP / total = 6 / 12 = 0.50
    assert pytest.approx(summary["unconditional_false_pass_rate"], 0.001) == 0.50

    # Verified Correct Delivery Rate = TP / total = 3 / 12 = 0.25
    assert pytest.approx(summary["verified_correct_delivery_rate"], 0.001) == 0.25

    # Final Correct Implementation Rate = (TP + FN) / total = (3 + 2) / 12 = 5 / 12 = 0.4166...
    assert pytest.approx(summary["final_correct_implementation_rate"], 0.001) == 5 / 12


def test_zero_pass_claims_no_divide_by_zero():
    # When no PASS claims exist, precision and false_pass_rate should safely be 0.0
    records = [{
        "condition_verdict": "FAIL",
        "ground_truth_verdict": "FAIL",
        "outcome": {"classification": "TRUE_FAIL"},
        "true_pass": False,
        "false_pass": False,
        "true_fail": True,
        "false_fail": False,
    }]
    summary = compute_condition_summary(records, "all_fail")
    assert summary["precision"] == 0.0
    assert summary["false_pass_rate"] == 0.0
    assert summary["reliability"] == 1.0

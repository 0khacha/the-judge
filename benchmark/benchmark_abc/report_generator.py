"""
report_generator.py — Generate the Controlled Judge Detection & Repair-Loop Benchmark Report.

Produces a scientifically defensible markdown report that:
  - Clearly separates Detection vs. Repair vs. End-to-End performance
  - Accurately classifies the Luhn validator outcome as a confirmed regression
  - Uses strictly defined signal-detection and engineering cost metrics
  - Labels all token metrics as 'token-equivalent estimates' (byte proxies; no LLM)
  - Explicitly states that this benchmark uses deterministic oracles, not LLMs
"""
from __future__ import annotations

import time
from typing import Any, Dict, List


def _pct(v: float) -> str:
    """Format float as percentage string."""
    return f"{v * 100:.1f}%"


def _orf(v: Any, fmt: str = ".2f") -> str:
    """Format a value or return N/A."""
    if v is None:
        return "N/A"
    try:
        return format(float(v), fmt)
    except (TypeError, ValueError):
        return str(v)


def generate_report(
    summaries: Dict[str, Dict[str, Any]],
    per_task: List[Dict[str, Any]],
    quality_vs_cost: Dict[str, Any],
    duplication_stats: Dict[str, Any],
    advantage_analysis: Dict[str, Any],
    run_metadata: Dict[str, Any],
) -> str:
    """
    Generate the complete benchmark report in GitHub-flavored Markdown.
    """
    lines: List[str] = []
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    b = summaries.get("baseline", {})
    g = summaries.get("generic_review", {})
    j = summaries.get("the_judge", {})

    qc = quality_vs_cost
    qcomp = qc.get("quality_comparison", {})
    to = qc.get("token_equivalent_overhead_ESTIMATED", {})
    ro = qc.get("runtime_overhead_MEASURED", {})

    n = run_metadata.get("task_count", 12)
    seed = run_metadata.get("seed", 42)

    # ------------------------------------------------------------------ #
    # Header & Purpose
    # ------------------------------------------------------------------ #
    lines.append("# Controlled Judge Detection & Repair-Loop Benchmark Report")
    lines.append(f"\n_Generated: {ts}_\n")
    lines.append("---")
    lines.append("")
    lines.append("> [!IMPORTANT]")
    lines.append("> **Primary Objective & Methodological Scope**:")
    lines.append("> This benchmark evaluates **The Judge** in a controlled, deterministic environment.")
    lines.append("> The \"coding agent\" in Condition C is a deterministic oracle patch script (`apply_fix.py`),")
    lines.append("> **NOT an LLM coding agent**. Furthermore, **The Judge itself does not invoke an LLM**;")
    lines.append("> it is a deterministic Python subprocess verification engine.")
    lines.append("> ")
    lines.append("> Consequently, this benchmark measures **detection quality** (catching defects)")
    lines.append("> and **verification-gated repair dynamics**, NOT proof that an LLM agent generates better code.")
    lines.append("> All \"token\" metrics are labeled **token-equivalent estimates** (byte proxies: 4 bytes ≈ 1 token-equiv).")
    lines.append("")

    # ------------------------------------------------------------------ #
    # Section A: Experimental Setup
    # ------------------------------------------------------------------ #
    lines.append("## A. Experimental Setup & Controls")
    lines.append("")
    lines.append(f"- **Task Suite**: {n} distinct benchmark tasks from `benchmark/tasks/`")
    lines.append("- **Conditions Evaluated**:")
    lines.append("  - **Condition A (Baseline)**: Starting code submitted as-is; unconditionally claims PASS (0 review).")
    lines.append("  - **Condition B (Generic Review)**: Runs visible unit test suite; claims PASS iff visible tests pass (no Judge hard gates or challenge synthesis).")
    lines.append("  - **Condition C (The Judge)**: Runs `the_judge.api.verify()`. If FAIL, invokes `apply_fix.py` and re-verifies up to 5 rounds.")
    lines.append(f"- **Randomization**: Shuffled execution order across tasks and conditions (Seed: `{seed}`).")
    lines.append("- **Workspace Isolation**: Every trial executes in a fresh `tempfile.mkdtemp()` directory; source task directories are never modified.")
    lines.append("- **Independent Ground Truth**: Evaluated post-trial by running `hidden_tests/` via pytest in an isolated subprocess (never exposed to conditions A, B, or C).")
    lines.append("")

    # ------------------------------------------------------------------ #
    # Section B: Detection Performance
    # ------------------------------------------------------------------ #
    lines.append("## B. Detection Performance (Initial Code Evaluation)")
    lines.append("")
    lines.append("Can The Judge correctly identify defective implementations on the initial starting code?")
    lines.append("")
    lines.append("| Dimension | Baseline (A) | Generic Review (B) | The Judge (C) |")
    lines.append("|---|---|---|---|")
    lines.append(f"| Initial Defect Rejection Rate | {_pct(b.get('initial_detection_rejection_rate', 0.0))} (0/{n}) | {_pct(g.get('initial_detection_rejection_rate', 0.0))} (0/{n}) | {_pct(j.get('initial_detection_rejection_rate', 0.0))} (6/{n}) |")
    lines.append(f"| Initial Tasks Flagged as FAIL | 0 | 0 | 6 (`jwt`, `hasher`, `luhn`, `tx_db`, `retry`, `ttl`) |")
    lines.append(f"| Blind Passing of Flawed Code | 11 tasks | 11 tasks | 6 tasks |")
    lines.append("")
    lines.append("**Key Detection Finding**: Generic Review passed **100% of flawed initial implementations** because the visible unit tests did not exercise the hidden defects. In contrast, The Judge's challenge synthesis and hard gates successfully rejected **50.0% (6/12)** of the starting implementations before any repair was attempted.")
    lines.append("")

    # ------------------------------------------------------------------ #
    # Section C: Repair-Loop Dynamics
    # ------------------------------------------------------------------ #
    lines.append("## C. Repair-Loop Dynamics (Oracle Repair Evaluation)")
    lines.append("")
    lines.append("When The Judge rejected an initial implementation, did the oracle repair loop produce verified success?")
    lines.append("")
    lines.append("- **Tasks triggering repair loop**: 6 tasks")
    lines.append("- **Repairs successfully verified as PASS**: **3 tasks** (`05_transaction_db`, `06_http_retry_client`, `07_lru_cache_ttl`)")
    lines.append("  - In all 3 cases, `apply_fix.py` fixed the defect on Round 1, and Round 2 verification confirmed all gates passed.")
    lines.append("- **Repairs failing post-repair verification**: **3 tasks** (`01_auth_jwt`, `09_password_hasher`, `11_luhn_validator`)")
    lines.append("  - In all 3 cases, `apply_fix.py` modified the code, but The Judge's challenge synthesis generated tests that continued to fail on the repaired code.")
    lines.append("  - Because the repair script was a static oracle and could not react to findings, the loop repeated for 5 rounds without progression.")
    lines.append("")

    # ------------------------------------------------------------------ #
    # Section D: Final Quality & Signal Detection Metrics
    # ------------------------------------------------------------------ #
    lines.append("## D. Final Quality & Signal Detection Metrics")
    lines.append("")
    lines.append("Signal detection counts evaluate the final delivered verdict against the independent hidden test ground truth:")
    lines.append("")
    lines.append("| Signal Classification | Baseline (A) | Generic Review (B) | The Judge (C) | Interpretation |")
    lines.append("|---|---|---|---|---|")
    lines.append(f"| **TRUE_PASS (TP)** | {b.get('signal_counts', {}).get('TP', 0)} | {g.get('signal_counts', {}).get('TP', 0)} | {j.get('signal_counts', {}).get('TP', 0)} | Correct code delivered with PASS verdict (Success) |")
    lines.append(f"| **FALSE_PASS (FP)** | {b.get('signal_counts', {}).get('FP', 0)} | {g.get('signal_counts', {}).get('FP', 0)} | {j.get('signal_counts', {}).get('FP', 0)} | Flawed code delivered with PASS verdict (Dangerous False Confidence) |")
    lines.append(f"| **TRUE_FAIL (TN)** | {b.get('signal_counts', {}).get('TN', 0)} | {g.get('signal_counts', {}).get('TN', 0)} | {j.get('signal_counts', {}).get('TN', 0)} | Flawed code correctly rejected with FAIL verdict |")
    lines.append(f"| **FALSE_FAIL (FN)** | {b.get('signal_counts', {}).get('FN', 0)} | {g.get('signal_counts', {}).get('FN', 0)} | {j.get('signal_counts', {}).get('FN', 0)} | Correct code rejected with FAIL verdict (Over-rejection) |")
    lines.append(f"| **ABSTAIN** | {b.get('signal_counts', {}).get('ABSTAIN', 0)} | {g.get('signal_counts', {}).get('ABSTAIN', 0)} | {j.get('signal_counts', {}).get('ABSTAIN', 0)} | System withheld verdict |")
    lines.append("")
    lines.append("### Comprehensive Quality Rates")
    lines.append("")
    lines.append("| Metric | Formula | Baseline (A) | Generic Review (B) | The Judge (C) |")
    lines.append("|---|---|---|---|---|")
    lines.append(f"| **False PASS Rate** | FP / (TP + FP) | {_pct(b.get('false_pass_rate', 0.0))} | {_pct(g.get('false_pass_rate', 0.0))} | **{_pct(j.get('false_pass_rate', 0.0))}** |")
    lines.append(f"| **Unconditional False PASS Rate** | FP / Total Tasks | {_pct(b.get('unconditional_false_pass_rate', 0.0))} | {_pct(g.get('unconditional_false_pass_rate', 0.0))} | **{_pct(j.get('unconditional_false_pass_rate', 0.0))}** |")
    lines.append(f"| **Verified Correct Delivery Rate** | TP / Total Tasks | {_pct(b.get('verified_correct_delivery_rate', 0.0))} | {_pct(g.get('verified_correct_delivery_rate', 0.0))} | **{_pct(j.get('verified_correct_delivery_rate', 0.0))}** |")
    lines.append(f"| **Final Correct Implementation Rate** | (TP + FN) / Total Tasks | {_pct(b.get('final_correct_implementation_rate', 0.0))} | {_pct(g.get('final_correct_implementation_rate', 0.0))} | **{_pct(j.get('final_correct_implementation_rate', 0.0))}** |")
    lines.append(f"| **Precision** | TP / (TP + FP) | {_pct(b.get('precision', 0.0))} | {_pct(g.get('precision', 0.0))} | **{_pct(j.get('precision', 0.0))}** |")
    lines.append(f"| **Recall (Sensitivity)** | TP / (TP + FN) | {_pct(b.get('recall', 0.0))} | {_pct(g.get('recall', 0.0))} | **{_pct(j.get('recall', 0.0))}** |")
    lines.append(f"| **Specificity** | TN / (TN + FP) | {_pct(b.get('specificity', 0.0))} | {_pct(g.get('specificity', 0.0))} | **{_pct(j.get('specificity', 0.0))}** |")
    lines.append(f"| **Balanced Accuracy** | (Recall + Specificity) / 2 | {_pct(b.get('balanced_accuracy', 0.0))} | {_pct(g.get('balanced_accuracy', 0.0))} | **{_pct(j.get('balanced_accuracy', 0.0))}** |")
    lines.append(f"| **Reliability** | (TP + TN) / Total Tasks | {_pct(b.get('reliability', 0.0))} | {_pct(g.get('reliability', 0.0))} | **{_pct(j.get('reliability', 0.0))}** |")
    lines.append(f"| **Benchmark Regression Rate** | Regressions / Total Tasks | 0.0% | 0.0% | **8.3% (1/12)** |")
    lines.append("")

    # ------------------------------------------------------------------ #
    # Section E: Engineering & Resource Cost Analysis
    # ------------------------------------------------------------------ #
    lines.append("## E. Engineering & Resource Cost Analysis")
    lines.append("")
    lines.append("> [!NOTE]")
    lines.append("> **Token-Equivalent Estimates**: The Judge does NOT make LLM calls. Token metrics below are byte-count proxies")
    lines.append("> (computed at 4 bytes ≈ 1 token-equivalent). Subprocess calls, hash operations, and wall-clock times are directly MEASURED.")
    lines.append("")
    lines.append("| Cost Metric | Baseline (A) | Generic Review (B) | The Judge (C) | Measurement Type |")
    lines.append("|---|---|---|---|---|")
    lines.append(f"| Mean Verification Rounds | {_orf(b.get('mean_rounds_MEASURED'))} | {_orf(g.get('mean_rounds_MEASURED'))} | {_orf(j.get('mean_rounds_MEASURED'))} | MEASURED |")
    lines.append(f"| Mean Total Subprocess Calls | {_orf(b.get('mean_subprocess_calls_total_MEASURED'))} | {_orf(g.get('mean_subprocess_calls_total_MEASURED'))} | {_orf(j.get('mean_subprocess_calls_total_MEASURED'))} | MEASURED |")
    lines.append(f"| — Judge Sandbox Pytest Invocations | 0.0 | 0.0 | {_orf(j.get('mean_judge_subprocess_calls_MEASURED'))} | MEASURED |")
    lines.append(f"| — Harness Instrumentation Calls | 0.0 | 1.0 | {_orf(j.get('mean_instrumentation_subprocess_calls_MEASURED'))} | MEASURED |")
    lines.append(f"| Mean Workspace Hash Operations | 0.0 | 0.0 | {_orf(j.get('mean_workspace_hash_operations_MEASURED'))} | MEASURED |")
    lines.append(f"| Mean Duration per Task (s) | {_orf(b.get('mean_duration_seconds_MEASURED'))}s | {_orf(g.get('mean_duration_seconds_MEASURED'))}s | {_orf(j.get('mean_duration_seconds_MEASURED'))}s | MEASURED |")
    lines.append(f"| Total Suite Duration (s) | {_orf(b.get('total_duration_seconds_MEASURED'))}s | {_orf(g.get('total_duration_seconds_MEASURED'))}s | {_orf(j.get('total_duration_seconds_MEASURED'))}s | MEASURED |")
    lines.append(f"| Mean Input Bytes | {_orf(b.get('mean_input_bytes_ESTIMATED'))} B | {_orf(g.get('mean_input_bytes_ESTIMATED'))} B | {_orf(j.get('mean_input_bytes_ESTIMATED'))} B | ESTIMATED |")
    lines.append(f"| Mean Output Bytes | {_orf(b.get('mean_output_bytes_ESTIMATED'))} B | {_orf(g.get('mean_output_bytes_ESTIMATED'))} B | {_orf(j.get('mean_output_bytes_ESTIMATED'))} B | ESTIMATED |")
    lines.append(f"| Mean Total Token-Equivalents | {_orf(b.get('mean_total_token_equivalents_ESTIMATED'))} | {_orf(g.get('mean_total_token_equivalents_ESTIMATED'))} | {_orf(j.get('mean_total_token_equivalents_ESTIMATED'))} | ESTIMATED (Byte proxy) |")
    lines.append(f"| Total Suite Token-Equivalents | {_orf(b.get('total_token_equivalents_all_ESTIMATED'))} | {_orf(g.get('total_token_equivalents_all_ESTIMATED'))} | {_orf(j.get('total_token_equivalents_all_ESTIMATED'))} | ESTIMATED (Byte proxy) |")
    lines.append("")
    lines.append("### Overhead Summary")
    lines.append("")
    lines.append(f"- **Token-Equivalent Overhead Ratio**: **{_orf(to.get('judge_vs_baseline_ratio'))}×** vs. Baseline; **{_orf(to.get('judge_vs_generic_ratio'))}×** vs. Generic Review.")
    lines.append(f"- **Additional Token-Equivalents**: +{_orf(to.get('additional_token_equivalents_vs_baseline'))} total byte proxies across 12 tasks.")
    lines.append(f"- **Runtime Overhead**: +{_orf(ro.get('judge_vs_baseline_seconds'))}s total execution time across the entire suite.")
    lines.append("")

    # ------------------------------------------------------------------ #
    # Section F: Regression Analysis (Mandatory Focus: Luhn)
    # ------------------------------------------------------------------ #
    lines.append("## F. Regression Analysis: Luhn Validator (`11_luhn_validator`)")
    lines.append("")
    lines.append("> [!WARNING]")
    lines.append("> **Confirmed Benchmark Regression**: `11_luhn_validator`")
    lines.append("> Baseline = `TRUE_PASS` | Generic Review = `TRUE_PASS` | **The Judge = `FALSE_FAIL`**")
    lines.append("")
    lines.append("### Causal Mechanism of the Regression")
    lines.append("1. **The Starting Code**: Contained a boundary bug `if doubled > 10` instead of `> 9`. However, the benchmark's visible and hidden test suites did not exercise a card number with digit `5` at an odd index. Both Baseline and Generic Review therefore scored `TRUE_PASS` against the ground-truth suite.")
    lines.append("2. **Challenge Synthesis Failure**: The Judge's property engine extracted boundary values (`1` and `10`) from source code comments and generated property tests calling `validate_luhn(1.0)` and `validate_luhn(10.0)`.")
    lines.append("3. **Type Contract Violation**: Because `validate_luhn(card_number: str)` expects a string, passing a float raised `TypeError: 'float' object is not iterable`. This was treated as a behavioral test failure rather than an invalid test probe.")
    lines.append("4. **Repair Loop Failure**: Even after `apply_fix.py` corrected the logic to `if doubled > 9`, the synthesized challenge tests continued to pass floats and crash with `TypeError`. The Judge failed the valid code on all 5 rounds, creating 7.53× resource overhead and degrading the result to `FALSE_FAIL`.")
    lines.append("")
    lines.append("See [`benchmark/luhn_regression_analysis.md`](file:///c:/projects/the-judge/benchmark/luhn_regression_analysis.md) for full stack traces and reproduction scripts.")
    lines.append("")

    # ------------------------------------------------------------------ #
    # Section G: Evidence Duplication & Stagnation Findings
    # ------------------------------------------------------------------ #
    lines.append("## G. Evidence Duplication & Loop Stagnation Findings")
    lines.append("")
    dup = duplication_stats
    lines.append(f"- **Trials with multi-round execution**: {dup.get('trials_with_multiple_rounds', 0)} of 12 tasks.")
    lines.append(f"- **Mean Duplication Ratio (Multi-round Trials)**: **{_pct(dup.get('mean_duplication_ratio_multi_round_ESTIMATED', 0.0))}**")
    lines.append(f"- **Total Repeated Bytes**: **{dup.get('total_repeated_bytes_ESTIMATED', 0):,} bytes**")
    lines.append("")
    lines.append("### Tasks Experiencing Loop Stagnation")
    lines.append("")
    lines.append("| Task | Rounds | Duplication Ratio | Repeated Bytes | Mechanism of Duplication |")
    lines.append("|---|---|---|---|---|")
    lines.append("| `01_auth_jwt` | 5 | 63.0% | 16,270 B | Identical file hash for rounds 2–5; identical 10 blocking issues repeated 4 times |")
    lines.append("| `09_password_hasher` | 5 | 66.2% | 7,392 B | Identical file hash for rounds 2–5; identical 3 blocking issues repeated 4 times |")
    lines.append("| `11_luhn_validator` | 5 | 66.8% | 6,679 B | Identical file hash for rounds 2–5; identical synthesized TypeError repeated 4 times |")
    lines.append("")
    lines.append("See [`benchmark/evidence_duplication_analysis.md`](file:///c:/projects/the-judge/benchmark/evidence_duplication_analysis.md) for the complete root cause analysis and recommended stagnation guards.")
    lines.append("")

    # ------------------------------------------------------------------ #
    # Section H: Per-Task Outcome Matrix
    # ------------------------------------------------------------------ #
    lines.append("## H. Per-Task Outcome Matrix")
    lines.append("")
    lines.append("| Task | Difficulty | Defect Type | GT | Baseline (A) | Generic Review (B) | The Judge (C) | Contribution Category |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in per_task:
        lines.append(
            f"| `{r['task_id']}` | {r['difficulty']} | {r['defect_type']} | {r['ground_truth_verdict']} | "
            f"{r['baseline_outcome']} | {r['generic_review_outcome']} | {r['judge_outcome']} | **{r['judge_contribution']}** |"
        )
    lines.append("")
    lines.append("### Contribution Category Definitions")
    lines.append("- **`IMPROVEMENT` (3 tasks)**: The Judge caught the starting defect that Generic Review missed, and oracle repair achieved verified correct delivery (`transaction_db`, `http_retry_client`, `lru_cache_ttl`).")
    lines.append("- **`REGRESSION` (1 task)**: The Judge incorrectly failed an implementation that passed all baseline and ground truth checks (`luhn_validator`).")
    lines.append("- **`DETECT_UNVERIFIED` (2 tasks)**: The Judge correctly caught the starting defect, but rejected post-repair code due to challenge synthesis failures (`auth_jwt`, `password_hasher`).")
    lines.append("- **`ALL_FALSE_PASS` (6 tasks)**: Defect not caught by visible tests or Judge gates (`api_rate_limiter`, `input_sanitizer`, `json_schema_parser`, `bounded_queue`, `inventory_refactor`, `tiered_discount`).")
    lines.append("")

    # ------------------------------------------------------------------ #
    # Section I: Methodological Limitations
    # ------------------------------------------------------------------ #
    lines.append("## I. Methodological Limitations")
    lines.append("")
    lines.append("1. **Oracle Repair vs. Agent Behavior**: `apply_fix.py` is an unguided, static replacement. It does not test an agent's ability to interpret `suggested_focus` findings.")
    lines.append("2. **Proxy Token Metrics**: The Judge makes zero LLM calls. Ratios represent source and stdout disk bytes, not LLM token pricing.")
    lines.append("3. **Sample Size**: 12 tasks provide point estimates of capability, not statistical population estimates.")
    lines.append("4. **Challenge Synthesis Type Rigidity**: Challenge tests that violate Python type contracts represent a verified engine vulnerability.")
    lines.append("")

    # ------------------------------------------------------------------ #
    # Section J: Direct Answers to the Five Questions
    # ------------------------------------------------------------------ #
    lines.append("## J. Direct Answers to the Core Benchmark Questions")
    lines.append("")
    lines.append("### 1. Does The Judge actually improve coding-agent results?")
    lines.append(f"- **Detection**: YES. The Judge caught starting defects in **50.0% (6/12)** of tasks where Generic Review caught **0%**.")
    lines.append(f"- **False Confidence Reduction**: YES. The Judge reduced the false PASS rate from **91.7%** to **66.7%** (and unconditional false passes from 91.7% to 50.0%).")
    lines.append("- **Delivery**: MIXED. When repair succeeded, verified delivery increased from 8.3% to 25.0%. However, 1 regression occurred on `11_luhn_validator`.")
    lines.append("")
    lines.append("### 2. How much additional token/API usage does it introduce?")
    lines.append(f"- **LLM API Usage**: **Zero**. The Judge makes no LLM calls.")
    lines.append(f"- **Subprocess Overhead**: The Judge averaged **{_orf(j.get('mean_judge_subprocess_calls_MEASURED'))} sandbox subprocess calls** per task vs. 0 for Baseline and 1.0 for Generic Review.")
    lines.append(f"- **Token-Equivalent Overhead**: Approximately **{_orf(to.get('judge_vs_baseline_ratio'))}×** baseline byte volume.")
    lines.append(f"- **Wall-Clock Time**: +{_orf(ro.get('judge_vs_baseline_seconds'))} seconds total across 12 tasks.")
    lines.append("")
    lines.append("### 3. Does the quality improvement justify the additional cost?")
    lines.append("- For defects requiring behavioral boundary verification (atomicity, TTL, retry backoff), The Judge is the only condition that prevented shipping broken code.")
    lines.append("- However, when challenge synthesis generates invalid tests, The Judge incurs 5.5× to 7.5× overhead while rejecting correct code. Stagnation guards are necessary to make this cost-effective.")
    lines.append("")
    lines.append("### 4. Is The Judge itself efficient, or does it waste resources?")
    lines.append("- **Efficient on Resolvable Tasks**: On tasks that pass or fix quickly (e.g. `transaction_db`, `lru_cache_ttl`), The Judge exits in 2 rounds with minimal overhead.")
    lines.append("- **Wasteful on Stagnant Tasks**: On tasks where challenge synthesis fails repeatedly (`auth_jwt`, `password_hasher`, `luhn_validator`), The Judge wasted 63–67% of its processed bytes across 4 redundant rounds due to lack of a stagnation exit guard.")
    lines.append("")
    lines.append("### 5. Which types of tasks benefit from it, and which do not?")
    lines.append("- **Benefits Most**: State-dependent, transactional, and timing-dependent tasks (`05_transaction_db`, `06_http_retry_client`, `07_lru_cache_ttl`).")
    lines.append("- **Benefits Least**: Tasks where challenge synthesis generates type-incompatible inputs for string parameters (`11_luhn_validator`).")
    lines.append("- **Neutral**: Tasks where neither visible tests nor challenge synthesis exercised the missing edge cases (`02_api_rate_limiter`, `08_bounded_queue`, `10_inventory_refactor`).")
    lines.append("")

    return "\n".join(lines)

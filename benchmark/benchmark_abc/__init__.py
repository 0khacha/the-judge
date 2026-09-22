"""
benchmark_abc — Independent A/B/C benchmark for The Judge.

Measures quality (false-PASS rate, reliability) and cost (subprocess calls,
bytes processed, wall-clock time) across three conditions:

  A — Baseline:       code submitted as-is, no review
  B — Generic Review: visible tests only, no Judge
  C — The Judge:      full verify() + evidence-gated repair loop

Run with:
    python -m benchmark.benchmark_abc.run_abc
"""

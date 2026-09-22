# benchmark_abc — A/B/C Benchmark for The Judge

Independent, rigorous A/B/C evaluation of The Judge's quality and cost.

## Purpose

Answers five questions with measured evidence:

1. Does The Judge actually improve coding-agent results?
2. How much additional resource usage does it introduce?
3. Does the quality improvement justify the additional cost?
4. Is The Judge itself efficient, or does it waste resources?
5. Which types of tasks benefit from it, and which do not?

## Structure

```
benchmark_abc/
  __init__.py             # Package init
  task_catalog.py         # 12-task catalog with difficulty/defect labels
  instrumentation.py      # Measurement utilities (MEASURED/ESTIMATED/UNAVAILABLE labels)
  independent_evaluator.py # Ground-truth evaluator (runs hidden tests)
  conditions.py           # Three experimental conditions (A/B/C)
  analysis.py             # Statistical and comparative analysis
  report_generator.py     # Markdown report generator
  run_abc.py              # Main runner (entry point)
  results/                # Created at runtime
    raw/                  # Per-trial JSONL records
    summaries/            # Per-condition JSON summaries
    metrics/              # Comparison and quality-vs-cost metrics
    report/               # Final benchmark report
```

## Reproducibility

### Setup

```bash
pip install the-judge  # or: pip install -e .
pip install pytest
```

### Run

From the project root:

```bash
python -m benchmark.benchmark_abc.run_abc
```

Options:

```
--tasks benchmark/tasks         Tasks directory (default: benchmark/tasks)
--results benchmark/benchmark_abc/results
                                Results directory
--seed 42                       Random seed for trial ordering
--runs 1                        Runs per task/condition (1 = single pass)
--max-judge-rounds 5            Max repair rounds for Condition C
```

### Re-run with different seed

```bash
python -m benchmark.benchmark_abc.run_abc --seed 123
```

## Important Limitations

1. **No LLM agent**: The "coding agent" is a pre-written oracle fix script (`apply_fix.py`).
   Results measure The Judge's detection quality, not its guidance quality.

2. **No LLM token counts**: The Judge is a deterministic subprocess engine.
   All "token" metrics are byte-count proxies labeled **ESTIMATED**.
   Subprocess calls and wall-clock time are labeled **MEASURED**.

3. **Single run per trial**: Statistical confidence requires ≥3 runs.
   Use `--runs 3` for better estimates (slower).

4. **12 tasks only**: Not expanded to avoid delaying the benchmark.

## Results

After running, see:

- `results/report/benchmark_report.md` — full human-readable report
- `results/metrics/comparison.json` — summary comparison JSON
- `results/metrics/per_task.json` — per-task outcome matrix
- `results/raw/run_*.jsonl` — complete auditable per-trial records

## Preserving existing benchmark

This benchmark is in a **new `benchmark/benchmark_abc/` directory**.
It does NOT modify:

- `benchmark/runners/benchmark_runner.py` (the original Gauntlet)
- `benchmark/tasks/` (the 12 task directories)
- `benchmark/evaluators/hidden_evaluator.py`
- `benchmark/results/` (existing results from 2026-09-15)
- Any files inside `the_judge/`

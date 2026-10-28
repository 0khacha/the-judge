#!/usr/bin/env python3
"""Regression audit: run `judge verify --json` on every labelled corpus variant.

For each task in tasks/ and each variant in it:

1. Ground truth: the variant's implementation is run against the task's hidden
   test (tasks/<task>/hidden/) in a scratch directory. The hidden test never
   enters the judged workspace.
2. Visible check: the same implementation is run against the visible tests the
   judge will see, to know which bugs the visible tests already catch.
3. Judge: a workspace is built from the variant's files plus the visible tests
   and `judge verify <ws> --json` is run on it. Variants with a baseline/ dir
   are judged inside a git repo whose HEAD holds the baseline files and whose
   working tree holds the variant's (tampered) files. They are judged a second
   time without git, reported separately as "<variant>[no-git]".

Metrics printed:
  * False FAIL rate      correct implementations judged FAIL (target 0)
  * False PASS rate      incorrect implementations judged PASS
  * ABSTAIN rate on correct implementations
  * Added value          bugs that pass the visible tests AND get a verdict that
                         differs from the verdict on the same task's correct
                         implementation. FAILs that also hit the correct code
                         do not count.

Usage:
    python tests/regression_audit/run_audit.py [--judge-src DIR] [--json-out FILE]
        [--no-tools] [--task SUBSTR] [--workers N]

--judge-src DIR  import the_judge from DIR (e.g. a git worktree of an older commit)
--no-tools       run the judge with a PATH that does not contain mypy/ruff
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

AUDIT_DIR = Path(__file__).resolve().parent
TASKS_DIR = AUDIT_DIR / "tasks"
REPO_ROOT = AUDIT_DIR.parent.parent


@dataclass
class Row:
    task: str
    variant: str
    label: str                # "correct" or "wrong" (from task.json)
    truth: str                # "correct" or "wrong" (hidden test result)
    passes_visible: bool
    git_baseline: bool
    decision: Optional[str]   # PASS / FAIL / ABSTAIN / ERROR / None
    score: float
    blocking: list
    error: str = ""


def _pytest(dirpath: Path, extra_env: Optional[dict] = None) -> bool:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(dirpath))
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(dirpath)],
        cwd=str(dirpath), env=env, stdin=subprocess.DEVNULL,
        capture_output=True, text=True, timeout=120,
    )
    return proc.returncode == 0


def _impl_files(variant_dir: Path) -> list[Path]:
    return [p for p in variant_dir.iterdir()
            if p.is_file() and p.suffix == ".py" and not p.name.startswith("test_")]


def _copy_impl(variant_dir: Path, dest: Path) -> None:
    for p in _impl_files(variant_dir):
        shutil.copy2(p, dest / p.name)


def _visible_tests(task_dir: Path, variant_dir: Path) -> dict[str, Path]:
    """Visible tests: task-level visible/ overridden by same-named files in the variant."""
    tests = {p.name: p for p in (task_dir / "visible").glob("test_*.py")}
    for p in variant_dir.glob("test_*.py"):
        tests[p.name] = p
    return tests


def _truth(task_dir: Path, variant_dir: Path) -> str:
    with tempfile.TemporaryDirectory() as d:
        dp = Path(d)
        _copy_impl(variant_dir, dp)
        for p in (task_dir / "hidden").glob("*.py"):
            shutil.copy2(p, dp / ("test_" + p.name))
        return "correct" if _pytest(dp) else "wrong"


def _passes_visible(task_dir: Path, variant_dir: Path) -> bool:
    with tempfile.TemporaryDirectory() as d:
        dp = Path(d)
        _copy_impl(variant_dir, dp)
        for name, p in _visible_tests(task_dir, variant_dir).items():
            shutil.copy2(p, dp / name)
        return _pytest(dp)


def _git(ws: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(ws), check=True, capture_output=True,
                   stdin=subprocess.DEVNULL)


def _build_workspace(task_dir: Path, variant_dir: Path, ws: Path, use_git: bool) -> None:
    baseline = variant_dir / "baseline"
    visible = _visible_tests(task_dir, variant_dir)
    if use_git and baseline.is_dir():
        _copy_impl(variant_dir, ws)
        for name, p in visible.items():
            shutil.copy2(baseline / name if (baseline / name).exists() else p, ws / name)
        _git(ws, "init", "-q")
        _git(ws, "-c", "user.name=audit", "-c", "user.email=audit@example.invalid",
             "add", "-A")
        _git(ws, "-c", "user.name=audit", "-c", "user.email=audit@example.invalid",
             "commit", "-q", "-m", "baseline")
    else:
        _copy_impl(variant_dir, ws)
    for name, p in visible.items():
        shutil.copy2(p, ws / name)
    judge_json = variant_dir / "judge.json"
    if judge_json.exists():
        shutil.copy2(judge_json, ws / "judge.json")


def _judge_env(no_tools: bool) -> dict:
    env = dict(os.environ)
    if no_tools:
        keep = []
        for entry in env.get("PATH", "").split(os.pathsep):
            if not entry:
                continue
            if any(os.path.exists(os.path.join(entry, exe + ext))
                   for exe in ("mypy", "ruff", "flake8") for ext in ("", ".exe")):
                continue
            keep.append(entry)
        env["PATH"] = os.pathsep.join(keep)
    return env


def _run_judge(ws: Path, judge_src: Optional[str], no_tools: bool) -> tuple:
    src = judge_src or str(REPO_ROOT)
    launcher = (
        "import sys; sys.path.insert(0, sys.argv.pop(1)); "
        "from the_judge.integrations.cli import main; sys.exit(main(sys.argv[1:]))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", launcher, src, "verify", str(ws), "--json"],
        cwd=tempfile.gettempdir(), env=_judge_env(no_tools), stdin=subprocess.DEVNULL,
        capture_output=True, text=True, timeout=600,
    )
    out = proc.stdout
    start = out.find("{")
    if start == -1:
        return None, 0.0, [], (proc.stderr or out)[-400:]
    try:
        data = json.loads(out[start:])
    except json.JSONDecodeError as exc:
        return None, 0.0, [], f"bad JSON: {exc}"
    return (str(data.get("decision", "")).upper() or None,
            float(data.get("numeric_score", 0.0)),
            list(data.get("blocking_issues", [])), "")


def _evaluate(task_dir: Path, entry: dict, judge_src, no_tools, use_git: bool) -> Row:
    variant_dir = task_dir / "variants" / entry["variant"]
    truth = _truth(task_dir, variant_dir)
    visible_ok = _passes_visible(task_dir, variant_dir)
    with tempfile.TemporaryDirectory() as parent:
        # Neutral workspace name so nothing leaks the variant label to the judge.
        ws = Path(parent) / "project"
        ws.mkdir()
        _build_workspace(task_dir, variant_dir, ws, use_git)
        decision, score, blocking, err = _run_judge(ws, judge_src, no_tools)
    has_baseline = (variant_dir / "baseline").is_dir()
    name = entry["variant"] if (use_git or not has_baseline) else entry["variant"] + "[no-git]"
    return Row(task_dir.name, name, entry["expected"], truth, visible_ok,
               use_git and has_baseline, decision, score, blocking, err)


def _jobs(task_filter: Optional[str]):
    for task_dir in sorted(p for p in TASKS_DIR.iterdir() if p.is_dir()):
        if task_filter and task_filter not in task_dir.name:
            continue
        meta = json.loads((task_dir / "task.json").read_text(encoding="utf-8"))
        for entry in meta["variants"]:
            yield task_dir, entry, True
            if (task_dir / "variants" / entry["variant"] / "baseline").is_dir():
                yield task_dir, entry, False


def _pct(n: int, d: int) -> str:
    return f"{n}/{d} ({(100.0 * n / d) if d else 0.0:.0f}%)"


def report(rows: list[Row]) -> dict:
    print()
    print(f"{'task':<24} {'variant':<34} {'truth':<8} {'vis':<4} {'decision':<8} score")
    print("-" * 90)
    for r in rows:
        mark = "" if r.label == r.truth else "  (!label mismatch)"
        print(f"{r.task:<24} {r.variant:<34} {r.truth:<8} {'ok' if r.passes_visible else 'x':<4} "
              f"{str(r.decision):<8} {r.score:5.1f}{mark}"
              + (f"  ERR {r.error[:80]}" if r.error else ""))

    correct = [r for r in rows if r.truth == "correct"]
    wrong = [r for r in rows if r.truth == "wrong"]
    decisions = ("PASS", "FAIL", "ABSTAIN")
    print("\nConfusion matrix (rows = hidden-test truth, cols = judge decision)")
    print(f"{'':<10}" + "".join(f"{d:>9}" for d in decisions) + f"{'other':>9}")
    for label, group in (("correct", correct), ("wrong", wrong)):
        counts = [sum(1 for r in group if r.decision == d) for d in decisions]
        other = len(group) - sum(counts)
        print(f"{label:<10}" + "".join(f"{c:>9}" for c in counts) + f"{other:>9}")

    correct_by_task = {}
    for r in correct:
        correct_by_task.setdefault(r.task, r.decision)
    sneaky = [r for r in wrong if r.passes_visible]
    added = [r for r in sneaky
             if r.task in correct_by_task and r.decision != correct_by_task[r.task]]
    added_fail = [r for r in added if r.decision == "FAIL"]

    metrics = {
        "false_fail": [sum(1 for r in correct if r.decision == "FAIL"), len(correct)],
        "false_pass": [sum(1 for r in wrong if r.decision == "PASS"), len(wrong)],
        "abstain_on_correct": [sum(1 for r in correct if r.decision == "ABSTAIN"), len(correct)],
        "pass_on_correct": [sum(1 for r in correct if r.decision == "PASS"), len(correct)],
        "bugs_passing_visible": len(sneaky),
        "added_value": [len(added), len(sneaky)],
        "added_value_as_fail": len(added_fail),
        "label_mismatches": sum(1 for r in rows if r.label != r.truth),
        "errors": sum(1 for r in rows if r.decision not in decisions),
    }
    print()
    print("False FAIL rate (correct -> FAIL):        " + _pct(*metrics["false_fail"]))
    print("False PASS rate (wrong -> PASS):          " + _pct(*metrics["false_pass"]))
    print("ABSTAIN rate on correct code:             " + _pct(*metrics["abstain_on_correct"]))
    print("PASS rate on correct code:                " + _pct(*metrics["pass_on_correct"]))
    print("Added value (bugs passing visible tests whose verdict differs from the")
    print("  task's correct implementation):          " + _pct(*metrics["added_value"])
          + f"  [{metrics['added_value_as_fail']} as FAIL]")
    for r in added:
        print(f"    - {r.task}/{r.variant}: {r.decision} (correct impl: {correct_by_task[r.task]})")
    if metrics["label_mismatches"]:
        print(f"WARNING: {metrics['label_mismatches']} variant(s) whose hidden-test truth "
              "disagrees with task.json")
    if metrics["errors"]:
        print(f"WARNING: {metrics['errors']} judge run(s) produced no decision")
    return metrics


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--judge-src", default=None)
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--no-tools", action="store_true")
    ap.add_argument("--task", default=None)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    jobs = list(_jobs(args.task))
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(
            lambda j: _evaluate(j[0], j[1], args.judge_src, args.no_tools, j[2]), jobs))
    metrics = report(rows)
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump({"metrics": metrics, "rows": [asdict(r) for r in rows]}, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Create fresh workspaces and per-run judge logging wrappers for the A/B experiment."""
import json
import os
import shutil

SCRATCH = r"C:/Users/moham/AppData/Local/Temp/claude/C--projects-the-judge/6207043a-0e2e-4938-b71c-7d30fd1878fc/scratchpad"
EVAL = r"C:/projects/the-judge/eval_results"
REAL_JUDGE = SCRATCH + "/venv_eval/Scripts/judge.exe"
PY = SCRATCH + "/venv_eval/Scripts/python.exe"
TASKS = ["T1_query_parser", "T2_rate_limiter", "T3_slugify", "T4_parallel_map", "T5_split_bill"]

WRAPPER = r'''"""Logging wrapper: snapshots the workspace, runs the installed judge unchanged, records output."""
import json, os, shutil, subprocess, sys, time
REAL = {real!r}
LOG = {log!r}
CAP = 5
os.makedirs(LOG, exist_ok=True)
n = len([d for d in os.listdir(LOG) if d.startswith("iter_")]) + 1
if n > CAP:
    sys.stdout.write(json.dumps({{"decision": "ERROR", "error": "iteration cap of 5 judge runs reached"}}))
    sys.exit(3)
snap = os.path.join(LOG, "iter_%d" % n)
shutil.copytree(os.getcwd(), os.path.join(snap, "workspace"),
                ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"))
t0 = time.time()
p = subprocess.run([REAL] + sys.argv[1:], capture_output=True, text=True, stdin=subprocess.DEVNULL)
with open(os.path.join(snap, "judge_stdout.txt"), "w", encoding="utf-8") as f:
    f.write(p.stdout)
with open(os.path.join(snap, "judge_stderr.txt"), "w", encoding="utf-8") as f:
    f.write(p.stderr)
with open(os.path.join(snap, "meta.json"), "w", encoding="utf-8") as f:
    json.dump({{"iteration": n, "args": sys.argv[1:], "exit_code": p.returncode,
               "seconds": round(time.time() - t0, 2), "started": t0}}, f)
sys.stdout.write(p.stdout)
sys.stderr.write(p.stderr)
sys.exit(p.returncode)
'''

manifest = []
for task in TASKS:
    for cond in ("A", "B"):
        for run in (1, 2, 3):
            rid = f"{task}__{cond}__r{run}"
            ws = f"{SCRATCH}/ws/{rid}"
            shutil.rmtree(ws, ignore_errors=True)
            os.makedirs(ws)
            for name in ("TASK.md", "test_visible.py"):
                shutil.copy(f"{EVAL}/tasks/{task}/{name}", f"{ws}/{name}")
            log = f"{EVAL}/runs/{rid}"
            shutil.rmtree(log, ignore_errors=True)
            os.makedirs(log)
            wrapper = None
            if cond == "B":
                wrapper = f"{SCRATCH}/eval_tools/judge_{rid}.py"
                os.makedirs(os.path.dirname(wrapper), exist_ok=True)
                with open(wrapper, "w", encoding="utf-8") as f:
                    f.write(WRAPPER.format(real=REAL_JUDGE, log=log))
            manifest.append({"id": rid, "task": task, "cond": cond, "run": run,
                             "workspace": ws, "log": log, "wrapper": wrapper})
with open(f"{EVAL}/03_manifest.json", "w", encoding="utf-8") as f:
    json.dump({"python": PY, "real_judge": REAL_JUDGE, "runs": manifest}, f, indent=1)
print(len(manifest), "runs prepared")

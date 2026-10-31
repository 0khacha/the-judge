"""Logging wrapper around the installed judge 1.0.1 (freeze is passed through,
verify is snapshotted and capped at 5 calls)."""
import json, os, shutil, subprocess, sys, time
REAL = 'C:/Users/moham/AppData/Local/Temp/claude/C--projects-the-judge/6207043a-0e2e-4938-b71c-7d30fd1878fc/scratchpad/venv_101/Scripts/judge.exe'
LOG = 'C:/projects/the-judge/eval_results/eval2/runs/T6_csv__B__r3'
CAP = 5
os.makedirs(LOG, exist_ok=True)
cmd = sys.argv[1] if len(sys.argv) > 1 else ""
ignore = shutil.ignore_patterns("__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache")
if cmd == "verify":
    n = len([d for d in os.listdir(LOG) if d.startswith("iter_")]) + 1
    if n > CAP:
        sys.stdout.write(json.dumps({"decision": "ERROR", "error": "iteration cap of 5 verify calls reached"}))
        sys.exit(3)
    snap = os.path.join(LOG, "iter_%d" % n)
else:
    n = len([d for d in os.listdir(LOG) if d.startswith("freeze_")]) + 1
    snap = os.path.join(LOG, "freeze_%d" % n)
shutil.copytree(os.getcwd(), os.path.join(snap, "workspace"), ignore=ignore)
t0 = time.time()
p = subprocess.run([REAL] + sys.argv[1:], capture_output=True, text=True, stdin=subprocess.DEVNULL)
for name, data in (("judge_stdout.txt", p.stdout), ("judge_stderr.txt", p.stderr)):
    with open(os.path.join(snap, name), "w", encoding="utf-8") as f:
        f.write(data)
with open(os.path.join(snap, "meta.json"), "w", encoding="utf-8") as f:
    json.dump({"n": n, "args": sys.argv[1:], "exit_code": p.returncode, "seconds": round(time.time() - t0, 2),
               "started": t0}, f)
sys.stdout.write(p.stdout)
sys.stderr.write(p.stderr)
sys.exit(p.returncode)

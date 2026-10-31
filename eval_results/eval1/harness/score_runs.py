"""Score every A/B run against the hidden tests (Step 3)."""
import json
import os
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

SCRATCH = r"C:/Users/moham/AppData/Local/Temp/claude/C--projects-the-judge/6207043a-0e2e-4938-b71c-7d30fd1878fc/scratchpad"
EVAL = r"C:/projects/the-judge/eval_results"
HID = SCRATCH + "/h_f1de26ffd59e"
PY = SCRATCH + "/venv_eval/Scripts/python.exe"
TASKS_DIR = SCRATCH + "/../tasks"  # subagent transcripts live next to the scratchpad
MOD = {"T1_query_parser": "querystring.py", "T2_rate_limiter": "ratelimit.py", "T3_slugify": "slug.py",
       "T4_parallel_map": "pmap.py", "T5_split_bill": "bill.py"}


def hidden_results(task, workspace):
    """Run the hidden tests against the solution module only. Returns {test_id: passed}."""
    module = os.path.join(workspace, MOD[task])
    if not os.path.exists(module):
        return None
    with tempfile.TemporaryDirectory() as d:
        shutil.copy(module, os.path.join(d, MOD[task]))
        shutil.copy(os.path.join(HID, task, "test_hidden.py"), os.path.join(d, "test_hidden.py"))
        xml = os.path.join(d, "junit.xml")
        subprocess.run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={xml}", d],
                       cwd=d, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=300,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        if not os.path.exists(xml):
            return {}
        out = {}
        for tc in ET.parse(xml).iter("testcase"):
            ok = tc.find("failure") is None and tc.find("error") is None and tc.find("skipped") is None
            out[tc.get("name")] = ok
        return out


def visible_pass(task, workspace):
    module = os.path.join(workspace, MOD[task])
    if not os.path.exists(module):
        return False
    with tempfile.TemporaryDirectory() as d:
        shutil.copy(module, os.path.join(d, MOD[task]))
        shutil.copy(os.path.join(EVAL, "tasks", task, "test_visible.py"), os.path.join(d, "test_visible.py"))
        p = subprocess.run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", d], cwd=d, capture_output=True,
                           text=True, stdin=subprocess.DEVNULL, timeout=300,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        return p.returncode == 0


def rate(res):
    return round(sum(res.values()) / len(res), 4) if res else 0.0


manifest = json.load(open(os.path.join(EVAL, "03_manifest.json"), encoding="utf-8"))
usage = {}
for line in open(os.path.join(EVAL, "04_agent_usage.jsonl"), encoding="utf-8"):
    if line.strip():
        r = json.loads(line)
        usage[r["id"]] = r

rows = []
for run in manifest["runs"]:
    rid, task, ws, log = run["id"], run["task"], run["workspace"], run["log"]
    if rid not in usage:
        continue  # agent not finished yet
    final_copy = os.path.join(log, "final_workspace")
    shutil.rmtree(final_copy, ignore_errors=True)
    shutil.copytree(ws, final_copy, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    final = hidden_results(task, ws)
    iters = sorted((d for d in os.listdir(log) if d.startswith("iter_")), key=lambda s: int(s.split("_")[1]))
    per_iter, decisions, regressions = [], [], 0
    for it in iters:
        res = hidden_results(task, os.path.join(log, it, "workspace"))
        per_iter.append(rate(res) if res is not None else None)
        try:
            out = open(os.path.join(log, it, "judge_stdout.txt"), encoding="utf-8").read()
            decisions.append(json.loads(out[out.index("{"):]).get("decision"))
        except (OSError, ValueError):
            decisions.append(None)
        run.setdefault("_iter_results", []).append(res or {})
    # Regressions: a hidden test that passed at some judged snapshot and fails in a later
    # snapshot or in the final workspace.
    seq = run.get("_iter_results", []) + [final or {}]
    for i, earlier in enumerate(seq[:-1]):
        for later in seq[i + 1:]:
            regressions += sum(1 for t, ok in earlier.items() if ok and later.get(t) is False)
            break  # compare each state with the next state only
    rows.append({
        "id": rid, "task": task, "cond": run["cond"], "run": run["run"],
        "hidden_pass_rate": rate(final) if final is not None else 0.0,
        "hidden_passed": sum((final or {}).values()), "hidden_total": len(final or {}),
        "hidden_failing": sorted(t for t, ok in (final or {}).items() if not ok),
        "visible_pass": visible_pass(task, ws),
        "judge_iterations": len(iters), "judge_decisions": decisions,
        "hidden_rate_per_iteration": per_iter, "regressions": regressions,
        "tokens": usage[rid]["tokens"], "tool_uses": usage[rid]["tool_uses"],
        "wall_s": round(usage[rid]["duration_ms"] / 1000, 1),
        "agent_files": sorted(f for f in os.listdir(ws) if not f.startswith(".") and f != "__pycache__"),
    })

with open(os.path.join(EVAL, "05_scores.json"), "w", encoding="utf-8") as f:
    json.dump(rows, f, indent=1)
for r in rows:
    print(f"{r['id']:26} hidden={r['hidden_passed']:>2}/{r['hidden_total']:<2} vis={'ok' if r['visible_pass'] else 'X'} "
          f"iters={r['judge_iterations']} dec={r['judge_decisions']} per_iter={r['hidden_rate_per_iteration']} "
          f"regr={r['regressions']} tok={r['tokens']} t={r['wall_s']}s")

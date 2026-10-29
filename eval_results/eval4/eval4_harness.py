"""Evaluation 4 harness (protocol: eval_results/PROTOCOL4.md).

  python eval4_harness.py pilot            # pilot workspaces (A only, 2 runs per candidate) + prompts
  python eval4_harness.py select           # pick tasks from scored pilot runs (pre-registered rule)
  python eval4_harness.py main             # main workspaces for selected tasks + wrappers + prompts
  python eval4_harness.py score [pilot|main]
  python eval4_harness.py accuracy         # judge on reference / wrong solutions, visible tests frozen first
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

SCRATCH = r"C:/Users/moham/AppData/Local/Temp/claude/C--projects-the-judge/6207043a-0e2e-4938-b71c-7d30fd1878fc/scratchpad"
PUBLIC = SCRATCH + "/eval4_public"
HIDDEN = SCRATCH + "/h4_2d56b47e9641"
OUT = r"C:/projects/the-judge/eval_results/eval4"
VENV = SCRATCH + "/venv_102"
PY = VENV + "/Scripts/python.exe"
JUDGE = VENV + "/Scripts/judge.exe"
WS = SCRATCH + "/ws4"
TOOLS = SCRATCH + "/eval4_tools"
PILOT_RUNS, MAIN_RUNS, CAP = 2, 5, 8
SKIP_DIRS = {".judge", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".git"}

PROMPT_A = """You are a coding agent working on a small Python task.

Workspace: {ws}
Python to use: {py} (pytest is installed in it)

Rules:
- Work only inside the workspace. Do not read, list or search any other directory or file on this machine.
- Read TASK.md in the workspace and create or change the module(s) it asks for, in the workspace.
- You may run tests from inside the workspace with: <python> -m pytest -q
- Do not install packages.

When you are done, reply with: the file(s) you created or changed, and one sentence on whether you believe the solution is complete."""

PROTOCOL_B = """
You also have The Judge (package the-judge-verify) available. Follow its protocol, quoted from its AGENTS.md:

```
1. Tests first. Before writing or changing the implementation, write tests for the
   behaviour the task asks for (normal cases, edge cases, invalid input) and run:
       judge freeze .
   If the user gave you tests, freeze them before you touch the code.
2. Implement (or change) the code. Do not edit the frozen tests.
3. Run: judge verify . --json
4. Do what next_actions[0] says. Every verdict has numbered next_actions, each with
   "step", "action", "detail" and, where useful, "test", "command", "guidance":
     done                         -> report PASS and numeric_score. Stop.
     fix_code / fix_regression    -> change the IMPLEMENTATION so the named test passes.
     restore_tests                -> undo your change to the named frozen test.
     cover_requirement            -> the named spec rule (R1, R2, ...) has no passing test:
                                     write one that checks the rule and names its id.
     add_test                     -> a planted bug at the named file:line went unnoticed:
                                     decide the correct behaviour there FROM THE SPEC, add a
                                     test for it; if that test fails, fix the code.
     write_tests / freeze_tests   -> do what "detail" says, then implement.
     stop                         -> stop and report loop.stuck_reason and the
                                     remaining next_actions to the user.
5. Go to 3. The judge counts iterations (.judge/history.json), reports regressions
   (passed before, fails now) and says "stuck" after 3 identical non-PASS results or
   5 runs without PASS.
```
What counts as evidence: a test is independent when it is unchanged since `judge freeze` (or since the last git commit) and the implementation changed after that. Tests written after the code must pass but cannot earn PASS on their own. That is why step 1 comes first. Correcting one of your own frozen tests and freezing again only costs that one test its independence.
Requirements checklist: the judge numbers the rules (list items) of TASK.md, SPEC.md or REQUIREMENTS.md as R1..Rn. `judge freeze` prints them and marks the ones no test names yet. Write a test per rule and name the id in a comment or docstring (`def test_unterminated_quote():  # R4`), so every rule is tested before you implement. PASS requires each rule to have a passing test that names it.
Mutation feedback: before PASS, the judge plants small bugs in the implementation (`<` -> `<=`, `+` -> `-`, a removed `raise`, ...) and reruns all tests on a copy of the workspace. If fewer than 85% are caught, the verdict is ABSTAIN with one `add_test` action per uncaught bug. Tests you add for them do not need to be frozen. Write them from the specification, not from what the code currently returns -- that is how they find bugs.
Rules for agents: never claim code works without running judge verify first; never edit, skip, delete, parametrize away or weaken a frozen test to make it pass (adding tests is always fine; if a frozen test is genuinely wrong, fix it, run judge freeze again and say which test you changed and why); parse the JSON output and follow next_actions in order; mypy/ruff findings are advisory; when loop.stuck is true, stop and report; report the decision and numeric_score in your summary.

In this environment, run the judge ONLY with these commands, from inside the workspace:
    judge freeze .          ->  <python> {wrapper} freeze .
    judge verify . --json   ->  <python> {wrapper} verify . --json
It is the installed judge (at most {cap} verify runs). Do not run the judge any other way, and do not read or modify that file."""

SUFFIX_B = "\n\nWhen you are done, reply with: the file(s) you created or changed, and one sentence on whether you believe the solution is complete. Also report the final judge decision and numeric_score."

WRAPPER = r'''"""Logging wrapper around the installed judge 1.0.2 (freeze passed through,
verify snapshotted and capped)."""
import json, os, shutil, subprocess, sys, time
REAL = {real!r}
LOG = {log!r}
WS = {ws!r}
CAP = {cap}
os.makedirs(LOG, exist_ok=True)
cmd = sys.argv[1] if len(sys.argv) > 1 else ""
ignore = shutil.ignore_patterns("__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache")
if cmd == "verify":
    n = len([d for d in os.listdir(LOG) if d.startswith("iter_")]) + 1
    if n > CAP:
        sys.stdout.write(json.dumps({{"decision": "ERROR", "error": "iteration cap of %d verify calls reached" % CAP}}))
        sys.exit(3)
    snap = os.path.join(LOG, "iter_%d" % n)
else:
    n = len([d for d in os.listdir(LOG) if d.startswith("freeze_")]) + 1
    snap = os.path.join(LOG, "freeze_%d" % n)
shutil.copytree(WS, os.path.join(snap, "workspace"), ignore=ignore)
t0 = time.time()
p = subprocess.run([REAL] + sys.argv[1:], capture_output=True, text=True, stdin=subprocess.DEVNULL)
for name, data in (("judge_stdout.txt", p.stdout), ("judge_stderr.txt", p.stderr)):
    with open(os.path.join(snap, name), "w", encoding="utf-8") as f:
        f.write(data)
with open(os.path.join(snap, "meta.json"), "w", encoding="utf-8") as f:
    json.dump({{"n": n, "args": sys.argv[1:], "cwd": os.getcwd(), "exit_code": p.returncode,
               "seconds": round(time.time() - t0, 2), "started": t0}}, f)
sys.stdout.write(p.stdout)
sys.stderr.write(p.stderr)
sys.exit(p.returncode)
'''


def candidates():
    return sorted(d for d in os.listdir(PUBLIC) if os.path.isdir(os.path.join(PUBLIC, d)))


def prepare(runs, phase):
    manifest = []
    for task, cond, run in runs:
        rid = f"{task}__{cond}__r{run}"
        ws, log = f"{WS}/{rid}", f"{OUT}/{phase}/{rid}"
        shutil.rmtree(ws, ignore_errors=True)
        shutil.rmtree(log, ignore_errors=True)
        os.makedirs(log)
        shutil.copytree(os.path.join(PUBLIC, task), ws, ignore=shutil.ignore_patterns(*SKIP_DIRS))
        prompt = PROMPT_A.format(ws=ws, py=PY)
        wrapper = None
        if cond == "B":
            wrapper = f"{TOOLS}/judge_{rid}.py"
            os.makedirs(TOOLS, exist_ok=True)
            with open(wrapper, "w", encoding="utf-8") as f:
                f.write(WRAPPER.format(real=JUDGE, log=log, ws=ws, cap=CAP))
            base = prompt.split("\n\nWhen you are done")[0]
            prompt = base + "\n" + PROTOCOL_B.format(wrapper=wrapper, cap=CAP) + SUFFIX_B
        os.makedirs(f"{OUT}/prompts", exist_ok=True)
        with open(f"{OUT}/prompts/{rid}.txt", "w", encoding="utf-8") as f:
            f.write(prompt)
        manifest.append({"id": rid, "task": task, "cond": cond, "run": run, "workspace": ws,
                         "log": log, "wrapper": wrapper})
    with open(f"{OUT}/manifest_{phase}.json", "w", encoding="utf-8") as f:
        json.dump({"python": PY, "judge": JUDGE, "runs": manifest}, f, indent=1)
    print(len(manifest), phase, "runs prepared")


def copy_code(src, dst):
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if not name.endswith(".py") or name.startswith("test_") or name.endswith("_test.py") \
                    or name == "conftest.py":
                continue
            rel = os.path.relpath(os.path.join(root, name), src)
            os.makedirs(os.path.dirname(os.path.join(dst, rel)), exist_ok=True)
            shutil.copy2(os.path.join(root, name), os.path.join(dst, rel))


def run_tests(code_dir, test_file):
    with tempfile.TemporaryDirectory() as d:
        copy_code(code_dir, d)
        shutil.copy(test_file, os.path.join(d, "test_zz_ground_truth.py"))
        xml = os.path.join(d, "junit.xml")
        subprocess.run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={xml}",
                        os.path.join(d, "test_zz_ground_truth.py")], cwd=d, capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=600,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=d))
        if not os.path.exists(xml):
            return {}
        out = {}
        for tc in ET.parse(xml).iter("testcase"):
            ok = all(tc.find(t) is None for t in ("failure", "error", "skipped"))
            out[tc.get("classname", "") + "::" + tc.get("name")] = ok
        return out


def total_hidden(task):
    """Number of hidden test cases, as collected against the reference solution."""
    ref = os.path.join(HIDDEN, task, "reference")
    with tempfile.TemporaryDirectory() as d:
        shutil.copytree(os.path.join(PUBLIC, task), d, dirs_exist_ok=True)
        copy_code(ref, d)
        return len(run_tests(d, os.path.join(HIDDEN, task, "test_hidden.py")))


def rate(res, n_expected):
    # Tests that could not even be collected (import error) count as failed.
    return round(sum(res.values()) / max(n_expected, len(res)), 4) if n_expected else 0.0


def judge_json(path):
    try:
        out = open(path, encoding="utf-8").read()
        return json.loads(out[out.index("{"):])
    except (OSError, ValueError):
        return {}


def score(phase):
    manifest = json.load(open(f"{OUT}/manifest_{phase}.json", encoding="utf-8"))
    usage = {}
    path = f"{OUT}/agent_usage.jsonl"
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                usage[r["id"]] = r
    expected = {}
    rows = []
    for run in manifest["runs"]:
        rid, task, ws, log = run["id"], run["task"], run["workspace"], run["log"]
        if rid not in usage:
            continue
        if task not in expected:
            expected[task] = total_hidden(task)
        hidden = os.path.join(HIDDEN, task, "test_hidden.py")
        final_copy = os.path.join(log, "final_workspace")
        shutil.rmtree(final_copy, ignore_errors=True)
        shutil.copytree(ws, final_copy, ignore=shutil.ignore_patterns(*(SKIP_DIRS - {".judge"})))
        final = run_tests(ws, hidden)
        # Eval 4: the original project test suite (PUBLIC/<task>/tests/), not the agent's copy.
        visible = {}
        tests_dir = os.path.join(PUBLIC, task, "tests")
        for name in sorted(os.listdir(tests_dir)):
            if name.startswith("test_") and name.endswith(".py"):
                visible.update({f"{name}::{k}": v for k, v in run_tests(ws, os.path.join(tests_dir, name)).items()})
        iters = sorted((d for d in os.listdir(log) if d.startswith("iter_")), key=lambda s: int(s.split("_")[1]))
        snaps, decisions, actions = [], [], []
        false_pass = false_fail = 0
        for it in iters:
            res = run_tests(os.path.join(log, it, "workspace"), hidden)
            snaps.append(res)
            data = judge_json(os.path.join(log, it, "judge_stdout.txt"))
            dec = data.get("decision")
            decisions.append(dec)
            actions.append([a.get("action") for a in data.get("next_actions") or []])
            correct = bool(res) and len(res) >= expected[task] and all(res.values())
            if dec == "PASS" and not correct:
                false_pass += 1
            if dec == "FAIL" and correct:
                false_fail += 1
        guided = [i for i, a in enumerate(actions) if a and a[0] in ("cover_requirement", "add_test")]
        exposed = sum(1 for i in guided if i + 1 < len(decisions) and decisions[i + 1] == "FAIL")
        seq = snaps + [final]
        regressions = sum(1 for a, b in zip(seq, seq[1:]) for t, ok in a.items() if ok and b.get(t) is False)
        first_pass = next((i + 1 for i, d in enumerate(decisions) if d == "PASS"), None)
        def kind_rate(prefix):
            sel = {k: v for k, v in final.items() if k.split("::")[-1].startswith(prefix)}
            return round(sum(sel.values()) / len(sel), 4) if sel else None

        rows.append({
            "id": rid, "task": task, "cond": run["cond"], "run": run["run"],
            "new_pass_rate": kind_rate("test_new_"), "reg_pass_rate": kind_rate("test_reg_"),
            "hidden_pass_rate": rate(final, expected[task]), "hidden_passed": sum(final.values()),
            "hidden_total": expected[task],
            "fully_correct": len(final) >= expected[task] and bool(final) and all(final.values()),
            "visible_pass": bool(visible) and all(visible.values()),
            "judge_iterations": len(iters), "freeze_calls": len([d for d in os.listdir(log) if d.startswith("freeze_")]),
            "decisions": decisions, "first_actions": [a[0] if a else None for a in actions],
            "iterations_to_pass": first_pass, "hidden_rate_per_iteration": [rate(s, expected[task]) for s in snaps],
            "cover_requirement_actions": sum(a.count("cover_requirement") for a in actions),
            "add_test_actions": sum(a.count("add_test") for a in actions),
            "guided_verifies": len(guided), "guided_then_fail": exposed,
            "regressions": regressions, "judge_false_pass": false_pass, "judge_false_fail": false_fail,
            "tokens": usage[rid]["tokens"], "tool_uses": usage[rid]["tool_uses"],
            "wall_s": round(usage[rid]["duration_ms"] / 1000, 1),
        })
    with open(f"{OUT}/scores_{phase}.json", "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=1)
    for r in rows:
        print(f"{r['id']:30} hidden={r['hidden_passed']:>3}/{r['hidden_total']:<3} vis={'ok' if r['visible_pass'] else 'X'} "
              f"it={r['judge_iterations']} dec={r['decisions']} first={r['first_actions']} fp={r['judge_false_pass']}")


def select():
    rows = json.load(open(f"{OUT}/scores_pilot.json", encoding="utf-8"))
    stats = []
    for task in candidates():
        rs = [r for r in rows if r["task"] == task]
        if len(rs) < PILOT_RUNS:
            print("pilot incomplete for", task)
            return
        mean = sum(r["hidden_pass_rate"] for r in rs) / len(rs)
        stats.append((mean, sum(r["fully_correct"] for r in rs), task))
    stats.sort()
    qualifying = [s for s in stats if s[0] <= 0.95]
    chosen = qualifying[:6] if len(qualifying) >= 4 else []
    result = {"pilot": [{"task": t, "pilot_mean": round(m, 4), "pilot_fully_correct": c} for m, c, t in stats],
              "qualifying": [t for _, _, t in qualifying], "selected": sorted(t for _, _, t in chosen),
              "verdict": "ok" if chosen else "insufficient headroom"}
    with open(f"{OUT}/selection.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1)
    print(json.dumps(result, indent=1))


def main_setup():
    sel = json.load(open(f"{OUT}/selection.json", encoding="utf-8"))["selected"]
    prepare([(t, c, r) for t in sel for c in ("A", "B") for r in range(1, MAIN_RUNS + 1)], "main")


def accuracy():
    rows = []
    base = f"{OUT}/judge_accuracy"
    for task in candidates():
        for kind in ("reference", "wrong_1", "wrong_2"):
            src = os.path.join(HIDDEN, task, kind)
            if not os.path.isdir(src):
                continue
            ws = os.path.join(base, f"{task}__{kind}", "workspace")
            shutil.rmtree(os.path.dirname(ws), ignore_errors=True)
            shutil.copytree(os.path.join(PUBLIC, task), ws)
            subprocess.run([JUDGE, "freeze", ws], capture_output=True, stdin=subprocess.DEVNULL)
            copy_code(src, ws)
            p = subprocess.run([JUDGE, "verify", ws, "--json", "--no-history"], capture_output=True,
                               text=True, stdin=subprocess.DEVNULL, timeout=1800)
            try:
                data = json.loads(p.stdout[p.stdout.index("{"):])
            except ValueError:
                data = {"decision": None, "raw": p.stdout[-1000:]}
            with open(os.path.join(os.path.dirname(ws), "judge.json"), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=1)
            rows.append({"task": task, "solution": kind, "decision": data.get("decision"),
                         "next": (data.get("next_actions") or [{}])[0].get("action")})
            print(json.dumps(rows[-1]))
    with open(f"{base}/results.json", "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=1)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "pilot":
        prepare([(t, "A", r) for t in candidates() for r in range(1, PILOT_RUNS + 1)], "pilot")
    elif cmd == "select":
        select()
    elif cmd == "main":
        main_setup()
    elif cmd == "score":
        score(sys.argv[2])
    elif cmd == "accuracy":
        accuracy()

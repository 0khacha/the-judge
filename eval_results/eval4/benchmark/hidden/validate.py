import os, re, shutil, subprocess, sys, tempfile, json
from _h import H, P
PY = sys.executable
def run(cwd, target):
    r = subprocess.run([PY, "-m", "pytest", "-q", target, "-p", "no:cacheprovider"], cwd=cwd, capture_output=True, text=True)
    out = r.stdout + r.stderr
    p = sum(int(x) for x in re.findall(r"(\d+) passed", out)); f = sum(int(x) for x in re.findall(r"(\d+) (?:failed|error)", out))
    return p, f
def build(tid, sol):
    d = tempfile.mkdtemp()
    shutil.copytree(os.path.join(P, tid), d, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__",".pytest_cache"))
    if sol:
        shutil.copytree(os.path.join(H, tid, sol), d, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(os.path.join(H, tid, "test_hidden.py"), d)
    return d
def lines(tid):
    n = 0
    for root, ds, fs in os.walk(os.path.join(P, tid)):
        if "tests" in root.split(os.sep) or "__pycache__" in root: continue
        for f in fs:
            if f.endswith(".py"): n += len(open(os.path.join(root, f), encoding="utf-8").read().splitlines())
    return n
only = sys.argv[1:]
out = []
for tid in sorted(os.listdir(P)):
    if not tid.startswith("D") or (only and tid not in only): continue
    th = open(os.path.join(H, tid, "test_hidden.py"), encoding="utf-8").read()
    nn = len(re.findall(r"^def test_new_", th, re.M)); nr = len(re.findall(r"^def test_reg_", th, re.M))
    res = {}
    for sol in [None, "reference", "wrong_1", "wrong_2"]:
        d = build(tid, sol)
        res[sol or "original"] = (run(d, "tests"), run(d, "test_hidden.py"))
        shutil.rmtree(d, ignore_errors=True)
    ok = (res["original"][0][1] == 0 and all(res[k][0][1] == 0 for k in ("reference","wrong_1","wrong_2"))
          and res["reference"][1][1] == 0 and res["reference"][1][0] >= 30 and res["wrong_1"][1][1] > 0 and res["wrong_2"][1][1] > 0)
    lab = json.load(open(os.path.join(H, tid, "label.json")))
    out.append(f"{tid} lines={lines(tid)} (label {lab['lines']}) new={nn} reg={nr} reqs={lab['change_requirements']} "
               + " ".join(f"{k}:tests(p{v[0][0]}/f{v[0][1]}),hidden(p{v[1][0]}/f{v[1][1]})" for k, v in res.items()) + f" VALID={ok}")
    print(out[-1], flush=True)
if not only: open(os.path.join(H, "validation.txt"), "w").write("\n".join(out) + "\n")

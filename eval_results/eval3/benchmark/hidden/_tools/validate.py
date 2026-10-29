import os, re, shutil, subprocess, sys, tempfile

PY = sys.executable
B = "C:/Users/moham/AppData/Local/Temp/claude/C--projects-the-judge/6207043a-0e2e-4938-b71c-7d30fd1878fc/scratchpad"
PUB = B + "/eval3_public"
H = B + "/h3_3591a54487f2"
only = sys.argv[1:]


def run(d, test):
    r = subprocess.run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", test], cwd=d,
                       capture_output=True, text=True)
    out = r.stdout + r.stderr
    p = re.search(r"(\d+) passed", out)
    f = re.search(r"(\d+) failed", out)
    e = re.search(r"(\d+) error", out)
    return (int(p.group(1)) if p else 0), (int(f.group(1)) if f else 0) + (int(e.group(1)) if e else 0), out


lines = []
for task in sorted(os.listdir(H)):
    if task.startswith("_") or not os.path.isdir(H + "/" + task):
        continue
    if only and task not in only:
        continue
    for sol in ("reference", "wrong_1", "wrong_2"):
        sd = "%s/%s/%s" % (H, task, sol)
        if not os.path.isdir(sd):
            continue
        tmp = tempfile.mkdtemp()
        shutil.copytree("%s/%s" % (PUB, task), tmp, dirs_exist_ok=True)
        shutil.copytree(sd, tmp, dirs_exist_ok=True)
        shutil.copy("%s/%s/test_hidden.py" % (H, task), tmp)
        vp, vf, vo = run(tmp, "test_visible.py")
        hp, hf, ho = run(tmp, "test_hidden.py")
        ok = (vf == 0 and vp > 0 and ((hf == 0 and hp >= 25) if sol == "reference" else hf > 0))
        line = "%s %s: visible %d passed %d failed; hidden %d passed %d failed [%s]" % (
            task, sol, vp, vf, hp, hf, "OK" if ok else "PROBLEM")
        print(line)
        lines.append(line)
        if not ok or "-v" in os.environ.get("VAL_V", ""):
            print(ho[-1500:] if sol == "reference" else vo[-800:])
        shutil.rmtree(tmp, ignore_errors=True)
if not only:
    open(H + "/validation.txt", "w").write("\n".join(lines) + "\n")

import os, shutil, subprocess, sys, tempfile
PUB, HID, PY = sys.argv[1], sys.argv[2], sys.argv[3]
MOD = {"T1_query_parser": "querystring.py", "T2_rate_limiter": "ratelimit.py", "T3_slugify": "slug.py",
       "T4_parallel_map": "pmap.py", "T5_split_bill": "bill.py"}
def run(task, impl, testfile):
    with tempfile.TemporaryDirectory() as d:
        shutil.copy(impl, os.path.join(d, MOD[task]))
        shutil.copy(testfile, os.path.join(d, "test_x.py"))
        p = subprocess.run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider", d], cwd=d, capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        last = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr[-200:]
        return p.returncode == 0, last
for task in sorted(MOD):
    for kind in ("reference", "broken"):
        impl = os.path.join(HID, task, kind + ".py")
        v = run(task, impl, os.path.join(PUB, task, "test_visible.py"))
        h = run(task, impl, os.path.join(HID, task, "test_hidden.py"))
        print(f"{task:17} {kind:9} visible={'pass' if v[0] else 'FAIL'}  hidden={'pass' if h[0] else 'FAIL'}  ({h[1]})")

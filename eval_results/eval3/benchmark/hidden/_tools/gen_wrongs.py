import importlib.util, os, shutil, sys

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
only = sys.argv[1:]
for fn in sorted(os.listdir(os.path.dirname(os.path.abspath(__file__)))):
    if not fn.startswith("wrong_"):
        continue
    task = fn[len("wrong_"):-3]
    if only and task not in only:
        continue
    spec = importlib.util.spec_from_file_location("m", os.path.join(os.path.dirname(os.path.abspath(__file__)), fn))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    ref = os.path.join(H, task, "reference")
    for n, files in m.PATCHES.items():
        dst = os.path.join(H, task, "wrong_%d" % n)
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(ref, dst)
        for rel, pairs in files.items():
            p = os.path.join(dst, rel)
            s = open(p, encoding="utf-8", newline="").read()
            for old, new in pairs:
                assert old in s, (task, n, rel, old)
                s = s.replace(old, new)
            open(p, "w", encoding="utf-8", newline="").write(s)
        for rel, content in getattr(m, "FULL", {}).get(n, {}).items():
            p = os.path.join(dst, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w", encoding="utf-8", newline="").write(content)

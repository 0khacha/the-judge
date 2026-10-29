import os, shutil
H = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(os.path.dirname(H), "eval4_public")
def rep(path, old, new):
    s = open(path, encoding="utf-8").read()
    assert s.count(old) == 1, (path, s.count(old), old)
    open(path, "w", encoding="utf-8", newline="\n").write(s.replace(old, new))
def mk(tid, name):
    """copy original (no tests, no TASK.md) to HIDDEN/tid/name"""
    dst = os.path.join(H, tid, name)
    if os.path.exists(dst): shutil.rmtree(dst)
    shutil.copytree(os.path.join(P, tid), dst, ignore=shutil.ignore_patterns("tests","TASK.md","__pycache__",".pytest_cache"))
    return dst
def clone(tid, src, name):
    dst = os.path.join(H, tid, name)
    if os.path.exists(dst): shutil.rmtree(dst)
    shutil.copytree(os.path.join(H, tid, src), dst, ignore=shutil.ignore_patterns("__pycache__",".pytest_cache"))
    return dst

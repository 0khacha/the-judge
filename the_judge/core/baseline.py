"""Compare the workspace's tests against a git baseline to detect test tampering.

When the workspace is inside a git repository, every test file that exists at the
baseline ref (default HEAD) is compared with the working tree:

* a test function that existed at the baseline and no longer exists anywhere;
* an assertion present at the baseline that is gone from that test;
* a skip / xfail marker (decorator or pytest.skip/xfail call) that was added.

Each is reported as a tampering issue, which blocks PASS. Adding tests or
assertions is never flagged. A test moved to another file is matched by name.
"""

import ast
import fnmatch
import os
import shutil
import subprocess
from typing import Any, Optional

from .test_discovery import discover_workspace_tests, read_pytest_config

_SKIP_MARKERS = ("skip", "skipif", "xfail")


class BaselineError(ValueError):
    """Raised when an explicitly requested baseline ref cannot be used."""


def _git(cwd: str, *args: str) -> Optional[str]:
    try:
        proc = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True,
            stdin=subprocess.DEVNULL, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout if proc.returncode == 0 else None


def _test_functions(source: str) -> dict[str, dict[str, Any]]:
    """Map 'Class.test_x' / 'test_x' -> {"asserts": [...], "skips": [...]}."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    out: dict[str, dict[str, Any]] = {}

    def visit(fn: ast.AST, qualname: str, class_skips: list[str]) -> None:
        asserts: list[str] = []
        skips = list(class_skips)
        for deco in getattr(fn, "decorator_list", []):
            text = ast.unparse(deco)
            if any(f"mark.{m}" in text for m in _SKIP_MARKERS):
                skips.append(text)
        for node in ast.walk(fn):
            if isinstance(node, ast.Assert):
                asserts.append(ast.unparse(node.test))
            elif isinstance(node, ast.With):
                for item in node.items:
                    text = ast.unparse(item.context_expr)
                    if text.startswith("pytest.raises"):
                        asserts.append(text)
            elif isinstance(node, ast.Call):
                text = ast.unparse(node.func)
                if text in ("pytest.skip", "pytest.xfail"):
                    skips.append(text)
        out[qualname] = {"asserts": asserts, "skips": skips}

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            visit(node, node.name, [])
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            class_skips = [ast.unparse(d) for d in node.decorator_list
                           if any(f"mark.{m}" in ast.unparse(d) for m in _SKIP_MARKERS)]
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name.startswith("test"):
                    visit(item, f"{node.name}.{item.name}", class_skips)
    return out


def compare_tests_to_baseline(abs_dir: str, ref: Optional[str] = None) -> dict[str, Any]:
    """Return {"ref", "checked", "issues": [{"kind", "file", "test", "detail"}]}.

    ref=None means HEAD; when the workspace is not a git repository (or has no
    commits) the comparison is skipped. An explicit ref that cannot be resolved
    raises BaselineError.
    """
    explicit = ref is not None
    ref = ref or "HEAD"
    result: dict[str, Any] = {"ref": ref, "checked": False, "issues": []}
    if shutil.which("git") is None:
        if explicit:
            raise BaselineError("--baseline requires git on PATH")
        return result
    top = _git(abs_dir, "rev-parse", "--show-toplevel")
    commit = _git(abs_dir, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}") if top else None
    if not top or not commit:
        if explicit:
            raise BaselineError(f"cannot resolve baseline ref {ref!r} in {abs_dir}")
        return result
    top = os.path.abspath(top.strip())
    prefix = os.path.relpath(abs_dir, top).replace(os.sep, "/")
    prefix = "" if prefix == "." else prefix + "/"

    patterns = read_pytest_config(abs_dir)["python_files"]
    listing = _git(top, "ls-tree", "-r", "--name-only", commit.strip(), "--", prefix or ".") or ""
    baseline_files = [
        p for p in listing.splitlines()
        if p.endswith(".py") and any(fnmatch.fnmatch(p.rsplit("/", 1)[-1], pat) for pat in patterns)
    ]

    current: dict[str, dict[str, Any]] = {}
    current_by_file: dict[str, dict[str, dict[str, Any]]] = {}
    for rel in discover_workspace_tests(abs_dir):
        with open(os.path.join(abs_dir, rel), encoding="utf-8") as f:
            funcs = _test_functions(f.read())
        current_by_file[rel.replace(os.sep, "/")] = funcs
        for name, info in funcs.items():
            current.setdefault(name, info)

    issues: list[dict[str, str]] = []
    for path in baseline_files:
        rel = path[len(prefix):]
        source = _git(top, "show", f"{commit.strip()}:{path}")
        if source is None:
            continue
        base_funcs = _test_functions(source)
        here = current_by_file.get(rel)
        file_gone = here is None and not os.path.exists(os.path.join(abs_dir, rel))
        # A deleted file whose tests all live on elsewhere was moved, not deleted.
        if file_gone and base_funcs and not all(n in current for n in base_funcs):
            issues.append({"kind": "deleted_test_file", "file": rel, "test": "",
                           "detail": f"test file {rel} was deleted"})
        for name, base in base_funcs.items():
            now = (here or {}).get(name) or current.get(name)
            if now is None:
                issues.append({"kind": "deleted_test", "file": rel, "test": name,
                               "detail": f"test {name} in {rel} was removed"})
                continue
            missing = [a for a in base["asserts"] if a not in now["asserts"]]
            if missing:
                issues.append({"kind": "removed_assertion", "file": rel, "test": name,
                               "detail": f"test {name} in {rel} lost assertion(s): "
                                         + "; ".join(missing)[:300]})
            added = [s for s in now["skips"] if s not in base["skips"]]
            if added:
                issues.append({"kind": "added_skip", "file": rel, "test": name,
                               "detail": f"test {name} in {rel} gained skip/xfail: "
                                         + ", ".join(added)})
    result["checked"] = True
    result["issues"] = issues
    return result

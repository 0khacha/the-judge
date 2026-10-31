"""Mutation feedback: find behaviour that no test checks.

The judge plants one small bug (a *mutant*) at a time in the implementation files the
tests import, and reruns the workspace test suite on a temporary copy of the workspace
(the workspace itself is never written). A mutant the suite still passes *survives*:
the tests cannot tell that code from the original, so the behaviour at that line is
unchecked. Survivors are reported as concrete next actions (file, line, change).

Mutation operators: comparison swaps (``<`` <-> ``<=``, ``==`` <-> ``!=``, ...),
arithmetic swaps (``+`` <-> ``-``, ...), ``and`` <-> ``or``, integer constant + 1,
negated ``if``/``while`` conditions and removed ``raise`` statements. Docstrings,
annotations, default arguments, f-strings and ``if __name__ == "__main__":`` blocks are
not mutated.

Some mutants are *equivalent* (they do not change behaviour) and can never be killed;
the score threshold leaves room for them. This is a test-strength signal, not a proof.
"""

import ast
import os
import shutil
import sys
import tempfile
import threading
import time
from typing import Any

from .independence import source_files
from .sandbox import SandboxRunner
from .test_discovery import EXCLUDED_DIRS, discover_workspace_tests, import_roots

THRESHOLD = 0.85
MAX_MUTANTS = 25
MAX_WORKERS = 4

_CMP = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt,
        ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.In: ast.NotIn, ast.NotIn: ast.In,
        ast.Is: ast.IsNot, ast.IsNot: ast.Is}
_BIN = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Div, ast.Div: ast.Mult,
        ast.FloorDiv: ast.Div, ast.Mod: ast.FloorDiv}
_SYM = {ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=", ast.Eq: "==",
        ast.NotEq: "!=", ast.In: "in", ast.NotIn: "not in", ast.Is: "is", ast.IsNot: "is not",
        ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.FloorDiv: "//",
        ast.Mod: "%", ast.And: "and", ast.Or: "or"}


def _is_main_guard(node: ast.If) -> bool:
    t = node.test
    return (isinstance(t, ast.Compare) and isinstance(t.left, ast.Name) and t.left.id == "__name__"
            and len(t.comparators) == 1 and isinstance(t.comparators[0], ast.Constant)
            and t.comparators[0].value == "__main__")


class _Mutator(ast.NodeTransformer):
    """Counts mutation sites in a fixed order; applies the one with index ``target``."""

    def __init__(self, target: int = -1) -> None:
        self.target = target
        self.sites: list[tuple[int, str]] = []   # (line, change)

    def _site(self, node: ast.AST, change: str) -> bool:
        self.sites.append((getattr(node, "lineno", 0), change))
        return len(self.sites) - 1 == self.target

    # Not mutated: signatures/annotations, f-strings, the main guard.
    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        node.body = [self.visit(s) for s in node.body]
        return node

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    def visit_Lambda(self, node: ast.Lambda) -> ast.AST:
        node.body = self.visit(node.body)
        return node

    def visit_AnnAssign(self, node: ast.AnnAssign) -> ast.AST:
        if node.value is not None:
            node.value = self.visit(node.value)
        return node

    def visit_JoinedStr(self, node: ast.JoinedStr) -> ast.AST:
        return node

    def visit_If(self, node: ast.If) -> ast.AST:
        if _is_main_guard(node):
            return node
        return self._negate(node)

    def visit_While(self, node: ast.While) -> ast.AST:
        return self._negate(node)

    def _negate(self, node: Any) -> ast.AST:
        hit = self._site(node, f"negate condition '{ast.unparse(node.test)}'")
        self.generic_visit(node)
        if hit:
            node.test = ast.UnaryOp(op=ast.Not(), operand=node.test)
        return node

    def visit_Raise(self, node: ast.Raise) -> ast.AST:
        if self._site(node, "remove raise"):
            return ast.copy_location(ast.Pass(), node)
        return node

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        self.generic_visit(node)
        for i, op in enumerate(node.ops):
            new = _CMP.get(type(op))
            if new and self._site(node, f"'{_SYM[type(op)]}' -> '{_SYM[new]}'"):
                node.ops[i] = new()
        return node

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        self.generic_visit(node)
        new = _BIN.get(type(node.op))
        if new and self._site(node, f"'{_SYM[type(node.op)]}' -> '{_SYM[new]}'"):
            node.op = new()
        return node

    def visit_BoolOp(self, node: ast.BoolOp) -> ast.AST:
        self.generic_visit(node)
        new = ast.Or if isinstance(node.op, ast.And) else ast.And
        if self._site(node, f"'{_SYM[type(node.op)]}' -> '{_SYM[new]}'"):
            node.op = new()
        return node

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        value = node.value
        if (isinstance(value, int) and not isinstance(value, bool)
                and self._site(node, f"{value} -> {value + 1}")):
            return ast.copy_location(ast.Constant(value=value + 1), node)
        return node


def generate_mutants(rel_path: str, source: str) -> list[dict[str, Any]]:
    """Every single-site mutant of one file: {file, line, change, code, source}."""
    try:
        counting = _Mutator()
        counting.visit(ast.parse(source))
    except SyntaxError:
        return []
    lines = source.splitlines()
    out = []
    for index, (line, change) in enumerate(counting.sites):
        mutator = _Mutator(target=index)
        tree = ast.fix_missing_locations(mutator.visit(ast.parse(source)))
        try:
            mutated = ast.unparse(tree)
            compile(mutated, rel_path, "exec")
        except (SyntaxError, ValueError):
            continue
        out.append({"file": rel_path, "line": line, "change": change,
                    "code": lines[line - 1].strip() if 0 < line <= len(lines) else "",
                    "source": mutated})
    return out


def _imported_top_levels(abs_dir: str, tests: list[str]) -> set[str]:
    names: set[str] = set()
    for rel in tests:
        try:
            with open(os.path.join(abs_dir, rel), encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                names.add(node.module.split(".")[0])
    return names


def _target_files(abs_dir: str, tests: list[str]) -> list[str]:
    """Implementation files belonging to a module or package the tests import."""
    imported = _imported_top_levels(abs_dir, tests)
    roots = [os.path.relpath(r, abs_dir).replace(os.sep, "/") for r in import_roots(abs_dir)]
    out = []
    for rel in sorted(source_files(abs_dir)):
        for root in roots:
            prefix = "" if root == "." else root + "/"
            if prefix and not rel.startswith(prefix):
                continue
            top = rel[len(prefix):].split("/")[0]
            if top.endswith(".py"):
                top = top[:-3]
            if top in imported:
                out.append(rel)
                break
    return out


def _select(mutants: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    """Spread the sample over distinct lines: first one mutant per line, then more."""
    by_line: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for m in mutants:
        by_line.setdefault((m["file"], m["line"]), []).append(m)
    groups = list(by_line.values())
    chosen: list[dict[str, Any]] = []
    depth = 0
    while len(chosen) < limit and any(len(g) > depth for g in groups):
        layer = [g[depth] for g in groups if len(g) > depth]
        room = limit - len(chosen)
        if len(layer) > room:
            step = len(layer) / room
            layer = [layer[int(i * step)] for i in range(room)]
        chosen.extend(layer)
        depth += 1
    return chosen


def _copy_workspace(abs_dir: str, dest: str) -> None:
    def ignore(path: str, names: list[str]) -> list[str]:
        return [n for n in names if n.startswith(".") or n in EXCLUDED_DIRS
                or n.endswith(".egg-info") or os.path.isfile(os.path.join(path, n, "pyvenv.cfg"))]
    shutil.copytree(abs_dir, dest, ignore=ignore)


def _run_suite(copy_dir: str, ini: str, tests: list[str], timeout: int) -> dict[str, Any]:
    roots = [copy_dir] + ([os.path.join(copy_dir, "src")] if os.path.isdir(os.path.join(copy_dir, "src")) else [])
    cmd = [sys.executable, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider",
           "-c", ini, "--rootdir", copy_dir] + [os.path.join(copy_dir, t) for t in tests]
    env = {"PYTHONPATH": os.pathsep.join(roots), "PYTHONDONTWRITEBYTECODE": "1"}
    return SandboxRunner.run_cmd(cmd, cwd=copy_dir, env=env, timeout=timeout)


def run_mutation(abs_dir: str, max_mutants: int = MAX_MUTANTS,
                 threshold: float = THRESHOLD) -> dict[str, Any]:
    abs_dir = os.path.abspath(abs_dir)
    start = time.time()
    result: dict[str, Any] = {"ran": False, "skipped_reason": None, "total": 0, "killed": 0,
                              "timeouts": 0, "score": 1.0, "threshold": threshold,
                              "survivors": [], "mutants": [], "seconds": 0.0}
    tests = discover_workspace_tests(abs_dir)
    if not tests:
        result["skipped_reason"] = "no workspace tests"
        return result
    candidates: list[dict[str, Any]] = []
    for rel in _target_files(abs_dir, tests):
        try:
            with open(os.path.join(abs_dir, rel), encoding="utf-8") as f:
                candidates.extend(generate_mutants(rel, f.read()))
        except (OSError, UnicodeDecodeError):
            continue
    mutants = _select(candidates, max_mutants)
    if not mutants:
        result["skipped_reason"] = "no mutable code in the modules the tests import"
        return result

    work = tempfile.mkdtemp(prefix="jm")
    try:
        ini = os.path.join(work, "pytest.ini")
        with open(ini, "w", encoding="utf-8") as f:
            f.write("[pytest]\n")
        workers = max(1, min(MAX_WORKERS, os.cpu_count() or 1, len(mutants)))
        copies = []
        for i in range(workers):
            dest = os.path.join(work, f"w{i}")
            _copy_workspace(abs_dir, dest)
            copies.append(dest)

        t0 = time.time()
        base = _run_suite(copies[0], ini, tests, timeout=300)
        if base["exit_code"] != 0:
            result["skipped_reason"] = "the test suite does not pass unmutated in a copy of the workspace"
            return result
        timeout = max(10, int((time.time() - t0) * 5) + 5)

        def worker(idx: int) -> None:
            copy_dir = copies[idx]
            for m in mutants[idx::workers]:
                path = os.path.join(copy_dir, m["file"])
                with open(path, encoding="utf-8") as f:
                    original = f.read()
                with open(path, "w", encoding="utf-8") as f:
                    f.write(m["source"])
                try:
                    res = _run_suite(copy_dir, ini, tests, timeout)
                finally:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(original)
                m["status"] = ("timeout" if res.get("timed_out")
                               else "survived" if res["exit_code"] == 0 else "killed")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(workers)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    finally:
        shutil.rmtree(work, ignore_errors=True)

    survivors = [m for m in mutants if m.get("status") == "survived"]
    killed = len(mutants) - len(survivors)
    result.update({
        "ran": True, "total": len(mutants), "killed": killed,
        "timeouts": sum(1 for m in mutants if m.get("status") == "timeout"),
        "score": round(killed / len(mutants), 3),
        "survivors": [{k: m[k] for k in ("file", "line", "change", "code")} for m in survivors],
        "mutants": [{k: m.get(k) for k in ("file", "line", "change", "status")} for m in mutants],
        "seconds": round(time.time() - start, 2),
    })
    return result


def summary(result: dict[str, Any] | None) -> dict[str, Any]:
    if not result:
        return {"ran": False}
    return {k: result[k] for k in ("ran", "skipped_reason", "total", "killed", "score", "threshold")}

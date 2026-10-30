"""Detect implementations that hard-code the expected outputs of the tests.

Narrow, static heuristic. Inputs:
  * literal assertions in the independent tests: ``assert f(<literals>) == <literal>``;
  * literal tables in the implementation: dict literals ``{key: value}`` and if-chains
    ``if a == 1 and b == 2: return <literal>`` / ``if (a, b) == (1, 2): return <literal>``.

The implementation is *suspected* when every literal assertion (at least one) is
answered by such a table entry: key == the call's arguments and value == the expected
result. A legitimate table (e.g. Roman numerals) is not suspected as long as some
literal assertion uses inputs that are not table keys. Assertions built from
parametrize arguments or variables are not analysed; see README "Known limitations".
"""

import ast
import os
from typing import Any, Optional

_MISSING = object()


def _literal(node: ast.AST) -> Any:
    try:
        return _norm(ast.literal_eval(node))
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        return _MISSING


def _norm(value: Any) -> Any:
    """Lists and tuples compare equal (tuple(xs) keys answer list arguments)."""
    if isinstance(value, (list, tuple)):
        return tuple(_norm(v) for v in value)
    return value


def _call_args(call: ast.Call) -> Optional[tuple]:
    if call.keywords:
        return None
    args = tuple(_literal(a) for a in call.args)
    return None if any(a is _MISSING for a in args) else args


def literal_assertions(test_sources: dict[str, str], names: set[str]) -> list[tuple[tuple, Any]]:
    """(args, expected) for `assert f(literals) == literal` in the named test functions."""
    found = []
    for source in test_sources.values():
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
        for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
            funcs += [n for n in cls.body if isinstance(n, ast.FunctionDef)]
        for fn in funcs:
            if fn.name not in names:
                continue
            for node in ast.walk(fn):
                if not (isinstance(node, ast.Assert) and isinstance(node.test, ast.Compare)
                        and len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.Eq)):
                    continue
                left, right = node.test.left, node.test.comparators[0]
                for call, other in ((left, right), (right, left)):
                    if isinstance(call, ast.Call):
                        args, expected = _call_args(call), _literal(other)
                        if args is not None and expected is not _MISSING:
                            found.append((args, expected))
                        break
    return found


def _cond_literals(test: ast.AST) -> Optional[tuple]:
    """Literals compared for equality in an if-condition, in source order."""
    if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And):
        parts = [_cond_literals(v) for v in test.values]
        known = [p for p in parts if p is not None]
        return None if len(known) < len(parts) else tuple(x for p in known for x in p)
    if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq):
        for side in (test.comparators[0], test.left):
            value = _literal(side)
            if value is not _MISSING:
                return value if isinstance(value, tuple) else (value,)
    return None


def literal_tables(impl_sources: dict[str, str]) -> list[tuple[Any, Any]]:
    """(key, value) pairs from dict literals and if-return chains in the implementation."""
    pairs = []
    for source in impl_sources.values():
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                for k, v in zip(node.keys, node.values):
                    key, value = (_literal(k) if k is not None else _MISSING), _literal(v)
                    if key is not _MISSING and value is not _MISSING:
                        pairs.append((key, value))
            elif isinstance(node, ast.If):
                key = _cond_literals(node.test)
                ret = next((s for s in node.body if isinstance(s, ast.Return)), None)
                if key is not None and ret is not None and ret.value is not None:
                    value = _literal(ret.value)
                    if value is not _MISSING:
                        pairs.append((key, value))
    return pairs


def _answers(args: tuple, expected: Any, pairs: list[tuple[Any, Any]]) -> bool:
    for key, value in pairs:
        if value != expected:
            continue
        if key == args or (len(args) == 1 and key == args[0]):
            return True
        if isinstance(key, tuple) and sorted(map(repr, key)) == sorted(map(repr, args)):
            return True
    return False


def detect(abs_dir: str, test_files: list[str], impl_files: list[str],
           independent: set[str]) -> dict[str, Any]:
    def read(paths: list[str]) -> dict[str, str]:
        out = {}
        for rel in paths:
            try:
                with open(os.path.join(abs_dir, rel), encoding="utf-8") as f:
                    out[rel] = f.read()
            except OSError:
                continue
        return out

    assertions = literal_assertions(read(test_files), independent)
    pairs = literal_tables(read(impl_files))
    answered = [a for a in assertions if _answers(a[0], a[1], pairs)]
    suspected = bool(assertions) and len(answered) == len(assertions)
    return {
        "suspected": suspected,
        "literal_assertions": len(assertions),
        "answered_by_literal_table": len(answered),
        "examples": [f"{args!r} -> {expected!r}" for args, expected in answered[:3]] if suspected else [],
    }

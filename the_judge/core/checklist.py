"""Requirement checklist: every rule of the task specification needs a passing test.

The rules are the list items (``-``, ``*``, ``+``, ``1.``) of TASK.md, SPEC.md and
REQUIREMENTS.md in the workspace root, outside fenced code blocks, numbered R1..Rn in
file order. A test *covers* Rk when its source -- the ``def`` line, its body and
docstring, its decorators and the comment lines right above it -- mentions ``Rk``.

The rules are taken from the spec as it was at the first ``judge freeze`` that saw a
spec, so deleting a rule from TASK.md later does not remove it from the checklist.
The judge cannot check that a test really exercises the rule it names; the checklist
makes sure no rule is forgotten.
"""

import ast
import os
import re
from typing import Any, Optional

SPEC_FILES = ("TASK.md", "SPEC.md", "REQUIREMENTS.md")
MIN_LENGTH = 15
_ITEM = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+(.*\S)\s*$")
_ID = re.compile(r"\bR(\d+)\b")


def extract_requirements(text: str, source: str = "TASK.md", start: int = 1) -> list[dict[str, Any]]:
    reqs: list[dict[str, Any]] = []
    in_code = False
    current: Optional[dict[str, Any]] = None
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            in_code = not in_code
            current = None
            continue
        if in_code:
            continue
        match = _ITEM.match(line)
        if match:
            current = {"text": match.group(2)}
            reqs.append(current)
        elif current is not None and line.strip() and line[:1].isspace():
            current["text"] += " " + line.strip()       # wrapped continuation line
        else:
            current = None
    out: list[dict[str, Any]] = []
    for item in reqs:
        if len(item["text"]) >= MIN_LENGTH:
            out.append({"id": f"R{start + len(out)}", "text": item["text"], "source": source})
    return out


def read_spec(abs_dir: str) -> dict[str, str]:
    spec = {}
    for name in SPEC_FILES:
        path = os.path.join(abs_dir, name)
        if os.path.isfile(path):
            with open(path, encoding="utf-8", errors="replace") as f:
                spec[name] = f.read()
    return spec


def requirements_from(spec: dict[str, str]) -> list[dict[str, Any]]:
    reqs: list[dict[str, Any]] = []
    for name in SPEC_FILES:
        if name in spec:
            reqs.extend(extract_requirements(spec[name], name, start=len(reqs) + 1))
    return reqs


def requirements(abs_dir: str, freezes: Optional[list[dict[str, Any]]] = None) -> list[dict[str, Any]]:
    """Rules of the earliest frozen spec, else of the current spec files."""
    for snap in freezes or []:
        if snap.get("spec"):
            return requirements_from(snap["spec"])
    return requirements_from(read_spec(abs_dir))


def covered_ids(test_sources: dict[str, str]) -> dict[str, list[str]]:
    """{requirement id: sorted test function names that mention it}."""
    found: dict[str, set[str]] = {}
    for source in test_sources.values():
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        lines = source.splitlines()
        funcs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
            funcs += [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for fn in funcs:
            if not fn.name.startswith("test"):
                continue
            first = min([fn.lineno] + [d.lineno for d in fn.decorator_list])
            while first > 1 and lines[first - 2].strip().startswith("#"):
                first -= 1
            segment = "\n".join(lines[first - 1:fn.end_lineno])
            for num in _ID.findall(segment):
                found.setdefault(f"R{int(num)}", set()).add(fn.name)
    return {rid: sorted(names) for rid, names in found.items()}


def check(reqs: list[dict[str, Any]], test_sources: dict[str, str],
          passed: list[str], failed: list[str]) -> dict[str, Any]:
    """Which requirements have at least one passing test that names them."""
    passed_base = {p.split("[", 1)[0] for p in passed}
    failed_base = {f.split("[", 1)[0] for f in failed}
    cover = covered_ids(test_sources)
    covered: list[str] = []
    uncovered: list[str] = []
    for req in reqs:
        tests = [t for t in cover.get(req["id"], []) if t in passed_base and t not in failed_base]
        (covered if tests else uncovered).append(req["id"])
    return {"requirements": reqs, "covered": covered, "uncovered": uncovered, "tests": cover}


def summary(info: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not info:
        return {"total": 0, "covered": [], "uncovered": []}
    return {"total": len(info["requirements"]), "covered": info["covered"], "uncovered": info["uncovered"]}

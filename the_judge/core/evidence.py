"""Ground Truth Evidence Extractor for The Judge v4.0."""

import ast as _ast_module
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from typing import Any, Optional

from .baseline import compare_tests_to_baseline
from .behavior_engine import BehaviorEngine
from .property_engine import generate_property_tests, untriggered_probes
from .sandbox import SandboxRunner
from .test_discovery import (
    discover_workspace_tests,
    import_roots,
    support_files,
    workspace_module_names,
)



def test_base_name(name: str) -> str:
    """`test_x[1-2]` -> `test_x` (pytest parametrize id stripped)."""
    return name.split("[", 1)[0]


def _is_tautology(test: "_ast_module.expr") -> bool:
    """An assertion condition that holds whatever the code under test does."""
    if isinstance(test, _ast_module.Constant):
        return bool(test.value)
    if isinstance(test, _ast_module.Compare) and len(test.ops) == 1:
        op, right = test.ops[0], test.comparators[0]
        # x == x, x is x, x <= x ...
        same_sides = _ast_module.dump(test.left) == _ast_module.dump(right)
        if same_sides and isinstance(op, (_ast_module.Eq, _ast_module.Is, _ast_module.LtE, _ast_module.GtE)):
            return True
        # x in (True, False): passes for any predicate result, right or wrong
        if isinstance(op, _ast_module.In) and isinstance(right, (_ast_module.Tuple, _ast_module.List, _ast_module.Set)):
            values = {e.value for e in right.elts if isinstance(e, _ast_module.Constant)}
            if len(values) == len(right.elts) and {True, False} <= values:
                return True
    # x is None or x is not None
    if isinstance(test, _ast_module.BoolOp) and isinstance(test.op, _ast_module.Or):
        dumps = []
        for val in test.values:
            if (isinstance(val, _ast_module.Compare) and len(val.ops) == 1
                    and isinstance(val.ops[0], (_ast_module.Is, _ast_module.IsNot))
                    and isinstance(val.comparators[0], _ast_module.Constant)
                    and val.comparators[0].value is None):
                dumps.append((_ast_module.dump(val.left), type(val.ops[0])))
        lefts = {d for d, _ in dumps}
        if any((d, _ast_module.Is) in dumps and (d, _ast_module.IsNot) in dumps for d in lefts):
            return True
    return False


def _is_existence_only(test: "_ast_module.expr") -> bool:
    """`x is not None`: on its own it does not check behaviour."""
    return (
        isinstance(test, _ast_module.Compare) and len(test.ops) == 1
        and isinstance(test.ops[0], _ast_module.IsNot)
        and isinstance(test.comparators[0], _ast_module.Constant)
        and test.comparators[0].value is None
    )


def _detect_vacuous_tests(source_code: str, workspace_modules: set[str]) -> set[str]:
    """Detect test functions that provide no meaningful behavioral evidence.

    A test is vacuous if it:
      - has no assertion (assert statement or pytest.raises), or
      - only has tautological assertions (assert True, x == x,
        `(...) in (True, False)`, `x is None or x is not None`), or
      - only asserts `x is not None`, or
      - never references any workspace module (doesn't exercise target code).

    Test methods of Test* classes are included and reported by method name.
    """
    try:
        tree = _ast_module.parse(source_code)
    except SyntaxError:
        return set()

    # Collect top-level imports to know which names map to workspace modules
    imported_names: set[str] = set()
    for node in _ast_module.walk(tree):
        if isinstance(node, _ast_module.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in workspace_modules:
                    imported_names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, _ast_module.ImportFrom):
            if node.module and any(
                node.module == m or node.module.startswith(m + ".")
                for m in workspace_modules
            ):
                for alias in node.names:
                    imported_names.add(alias.asname or alias.name)

    # All names that could reference target code
    target_names = workspace_modules | imported_names

    functions = []
    for node in tree.body:
        if isinstance(node, _ast_module.FunctionDef):
            functions.append(node)
        elif isinstance(node, _ast_module.ClassDef) and node.name.startswith("Test"):
            functions.extend(n for n in node.body if isinstance(n, _ast_module.FunctionDef))

    vacuous: set[str] = set()
    for node in functions:
        if not node.name.startswith("test_"):
            continue

        has_meaningful_assert = False
        references_target = False

        for child in _ast_module.walk(node):
            if isinstance(child, _ast_module.Assert):
                if _is_tautology(child.test) or _is_existence_only(child.test):
                    continue
                has_meaningful_assert = True
            # pytest.raises(...) asserts that the code under test raises
            if (
                isinstance(child, _ast_module.Attribute)
                and child.attr == "raises"
                and isinstance(child.value, _ast_module.Name)
                and child.value.id == "pytest"
            ):
                has_meaningful_assert = True

            # Check if any name references a workspace module or imported symbol
            if isinstance(child, _ast_module.Name) and child.id in target_names:
                references_target = True
            if isinstance(child, _ast_module.Attribute):
                if isinstance(child.value, _ast_module.Name) and child.value.id in target_names:
                    references_target = True

        if not has_meaningful_assert or not references_target:
            vacuous.add(node.name)

    return vacuous


def run_command(cmd: list[str], cwd: str, env: Optional[dict[str, str]] = None) -> dict[str, Any]:
    """Execute a subprocess command and return exit code, stdout, stderr."""
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "error": None,
        }
    except Exception as e:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": str(e),
            "error": str(e),
        }


def _run_type_checker(abs_dir: str, cache_dir: str) -> dict[str, Any]:
    if shutil.which("mypy") is None:
        return {"exit_code": -1, "error_count": 0, "raw_output": "", "available": False,
                "tool": "mypy"}
    res = run_command(
        ["mypy", "--ignore-missing-imports", "--follow-imports=skip",
         "--cache-dir", os.path.join(cache_dir, "mypy"), "."],
        cwd=abs_dir,
    )
    if res["exit_code"] == -1:
        return {"exit_code": -1, "error_count": 0, "raw_output": res["stderr"][:2048],
                "available": False, "tool": "mypy"}
    # Only genuine "file:line: error:" lines count. mypy also exits non-zero for
    # configuration problems (exit 2), which are not type errors in the target code.
    err_cnt = len(re.findall(r": error:", res["stdout"]))
    return {
        "exit_code": res["exit_code"],
        "error_count": err_cnt,
        "raw_output": (res["stdout"] + res["stderr"])[:2048],
        "available": True,
        "tool": "mypy",
    }


def _run_linter(abs_dir: str) -> dict[str, Any]:
    if shutil.which("ruff") is not None:
        cmd, tool = ["ruff", "check", ".", "--no-cache", "--output-format=concise"], "ruff"
    elif shutil.which("flake8") is not None:
        cmd, tool = ["flake8", "."], "flake8"
    else:
        return {"exit_code": -1, "error_count": 0, "raw_output": "", "available": False,
                "tool": None}
    res = run_command(cmd, cwd=abs_dir)
    if res["exit_code"] == -1:
        return {"exit_code": -1, "error_count": 0, "raw_output": res["stderr"][:2048],
                "available": False, "tool": tool}
    err_cnt = len(re.findall(r"^.+?:\d+:\d+: ", res["stdout"], flags=re.MULTILINE))
    if err_cnt == 0 and res["exit_code"] != 0:
        err_cnt = 1
    return {
        "exit_code": res["exit_code"],
        "error_count": err_cnt,
        "raw_output": res["stdout"][:2048],
        "available": True,
        "tool": tool,
    }


def parse_pytest_output(stdout: str, stderr: str, exit_code: int) -> dict[str, Any]:
    """Parse pytest output to extract passed and failed test names."""
    passed_tests: list[str] = []
    failed_tests: list[str] = []

    combined = stdout + "\n" + stderr

    if "<?xml version=" in stdout or "<?xml version=" in stderr:
        try:
            import xml.etree.ElementTree as ET
            # find xml content
            xml_str = ""
            in_xml = False
            for line in combined.splitlines():
                if line.startswith("<?xml"):
                    in_xml = True
                if in_xml:
                    xml_str += line + "\n"
                if in_xml and line.strip() == "</testsuites>":
                    break
            
            tree = ET.fromstring(xml_str)
            for testcase in tree.findall('.//testcase'):
                name = testcase.get('name')
                if testcase.find('failure') is not None or testcase.find('error') is not None:
                    if name not in failed_tests:
                        failed_tests.append(name)
                else:
                    if name not in passed_tests:
                        passed_tests.append(name)
        except Exception:
            pass
            
    if not passed_tests and not failed_tests:
        for line in combined.splitlines():
            line = line.strip()
            if " PASSED" in line or line.endswith(" PASSED"):
                raw_name = line.split(" PASSED")[0].split()[-1]
                test_name = raw_name.split("::")[-1] if "::" in raw_name else raw_name
                if test_name and test_name not in passed_tests:
                    passed_tests.append(test_name)
            elif " FAILED" in line or line.endswith(" FAILED"):
                raw_name = line.split(" FAILED")[0].split()[-1]
                test_name = raw_name.split("::")[-1] if "::" in raw_name else raw_name
                if test_name and test_name not in failed_tests:
                    failed_tests.append(test_name)

    total_tests = len(passed_tests) + len(failed_tests)

    return {
        "exit_code": exit_code,
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "raw_stdout": stdout[:4096],
        "raw_stderr": stderr[:4096],
    }


def capture_evidence(
    workspace_dir: str,
    output_file: Optional[str] = None,
    task_spec: Optional[dict[str, Any]] = None,
    baseline: Optional[str] = None,
) -> dict[str, Any]:
    """Capture ground truth evidence from workspace_dir.

    baseline: git ref the workspace tests are compared against for tampering
        (default HEAD when the workspace is a git repository).
    """
    abs_dir = os.path.abspath(workspace_dir)
    # Resolve the baseline first so an unusable explicit --baseline fails fast.
    test_tampering = compare_tests_to_baseline(abs_dir, baseline)

    # 1. Synthesize property tests & black-box probes
    candidates = generate_property_tests(abs_dir, task_spec=task_spec)
    beh_engine = BehaviorEngine(seed=98765)
    probes = beh_engine.generate_behavioral_probes(abs_dir)

    test_scripts: list[tuple[str, str]] = []

    # Map expected challenge function names
    expected_challenges: list[str] = []

    for idx, cand in enumerate(candidates):
        filename = f"_synthesized_property_tests_{idx}.py"
        test_scripts.append((filename, cand.challenge_code))
        for line in cand.challenge_code.splitlines():
            if line.strip().startswith("def test_"):
                fn_name = line.strip().split("(")[0].replace("def ", "").strip()
                expected_challenges.append(fn_name)

    for idx, probe in enumerate(probes):
        filename = f"_synthesized_probe_{idx}.py"
        test_scripts.append((filename, probe.executable_code))
        for line in probe.executable_code.splitlines():
            if line.strip().startswith("def test_"):
                fn_name = line.strip().split("(")[0].replace("def ", "").strip()
                expected_challenges.append(fn_name)

    # Workspace tests, discovered recursively the way pytest would (testpaths,
    # python_files, norecursedirs; venvs/hidden dirs/node_modules excluded). They are
    # copied under a sub-directory of the sandbox with their relative layout, plus
    # the conftest.py files and sibling helpers they import.
    visible_tests = discover_workspace_tests(abs_dir)
    # Sandbox sub-directory for the workspace's tests; randomized per run so tests
    # cannot recognise the sandbox from a fixed directory name.
    suite_dir = uuid.uuid4().hex[:10]
    support: list[tuple[str, str]] = []
    for rel in support_files(abs_dir, visible_tests):
        with open(os.path.join(abs_dir, rel), encoding="utf-8") as f:
            support.append((os.path.join(suite_dir, rel), f.read()))
    for vt in visible_tests:
        with open(os.path.join(abs_dir, vt), encoding="utf-8") as f:
            content = f.read()
        test_scripts.append((os.path.join(suite_dir, vt), content))
        # P3 fix: extract test function names from visible test files and add them to
        # expected_challenges so that collection tampering (conftest hijack, etc.) is
        # detectable even when no judge.json contract is present.
        import ast as _ast
        try:
            tree = _ast.parse(content, filename=vt)
            for node in _ast.walk(tree):
                if isinstance(node, _ast.FunctionDef) and node.name.startswith("test_"):
                    if node.name not in expected_challenges:
                        expected_challenges.append(node.name)
        except Exception:
            pass  # Unparseable file — skip manifest tracking for it

    # 2. Run isolated anonymous sandbox
    sandbox_res = SandboxRunner.execute_in_anonymous_sandbox(
        abs_dir,
        test_scripts=test_scripts,
        pytest_args=["-vv"],
        timeout=30,
        support_files=support,
        import_roots=import_roots(abs_dir),
    )

    passed_tests = sandbox_res["passed"]
    failed_tests = sandbox_res["failed"]

    # Compare executed challenges against expected manifest
    skipped_tests = sandbox_res.get("skipped", [])
    # A skipped test was collected and run (it is not missing), but proves nothing.
    # pytest reports parametrized cases as name[param-id]; the manifest holds the
    # function name, so a function counts as executed when any case of it ran.
    all_executed = {test_base_name(t) for t in (*passed_tests, *failed_tests, *skipped_tests)}
    runner_error = sandbox_res.get("runner_error")
    # Nothing ran at all when the runner failed to start: nothing is "missing".
    missing_challenges = [] if runner_error else [
        ch for ch in expected_challenges if ch not in all_executed
    ]

    test_suite_data = {
        "exit_code": sandbox_res["exit_code"],
        "runner_error": runner_error,
        "total_tests": len(passed_tests) + len(failed_tests),
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "raw_stdout": sandbox_res["stdout"][:4096],
        "raw_stderr": sandbox_res["stderr"][:4096],
    }

    # 3/4. Optional static tools (discovered on PATH). A missing tool is reported as
    # unavailable; the score engine treats that as information, not as a blocker.
    # Caches are redirected to a throwaway directory so nothing is left in the
    # user's workspace.
    with tempfile.TemporaryDirectory() as tool_cache:
        type_checker_data = _run_type_checker(abs_dir, tool_cache)
        linter_data = _run_linter(abs_dir)

    # 5. Build test provenance mapping
    candidate_conf = {}
    judge_authored_tests = set()
    for cand in candidates:
        for line in cand.challenge_code.splitlines():
            if line.strip().startswith("def test_"):
                fn_name = line.strip().split("(")[0].replace("def ", "").strip()
                candidate_conf[fn_name] = cand.confidence
                judge_authored_tests.add(fn_name)
    for probe in probes:
        for line in probe.executable_code.splitlines():
            if line.strip().startswith("def test_"):
                fn_name = line.strip().split("(")[0].replace("def ", "").strip()
                judge_authored_tests.add(fn_name)

    test_provenance: dict[str, dict[str, Any]] = {}
    for t in passed_tests + failed_tests:
        if t in judge_authored_tests:
            # Structurally verified: this test was written by the Judge
            family_key = (
                "prop_boundary" if "boundary" in t
                else ("prop_idempotency" if "idempotency" in t else "prop_isolation")
            )
            test_provenance[t] = {
                "source": "judge_challenge_test",
                "independence_level": "externally_verified",
                "property_family": family_key,
                "confidence": candidate_conf.get(t, "HIGH"),
            }
        else:
            test_provenance[t] = {
                "source": "public_visible_test" if not t.startswith("test_agent_") else "agent_authored_test",
                "independence_level": "externally_verified" if not t.startswith("test_agent_") else "agent_controlled",
                "property_family": "public_workspace_tests",
                "confidence": "MEDIUM",
            }

    # Skipped workspace tests are reported (they hide behaviour); skipped judge probes
    # simply did not apply to this code and are recorded as "not run".
    test_suite_data["skipped_tests"] = [t for t in skipped_tests if t not in judge_authored_tests]
    test_suite_data["skipped_probes"] = [t for t in skipped_tests if t in judge_authored_tests]

    # Which judge probes ran (and how they ended) and which did not run because no
    # keyword trigger matched. Reported so a verdict never implies a check that
    # did not happen.
    probe_ran = []
    for cand in candidates:
        names = [ln.strip().split("(")[0][len("def "):] for ln in cand.challenge_code.splitlines()
                 if ln.strip().startswith("def test_")]
        for name in names:
            outcome = (
                "failed" if name in failed_tests
                else "passed" if name in passed_tests
                else "skipped" if name in skipped_tests
                else "missing"
            )
            probe_ran.append({"kind": cand.kind, "module": cand.source_module,
                              "symbol": cand.source_symbol, "test": name, "outcome": outcome})
    probe_coverage = {
        "triggers": "heuristic, keyword-based (see README 'Judge probes')",
        "ran": probe_ran,
        "not_run": untriggered_probes(abs_dir, candidates),
    }

    # 6. Detect vacuous tests in workspace test files
    workspace_modules = workspace_module_names(abs_dir)

    vacuous_tests: list[str] = []
    for vt in visible_tests:
        with open(os.path.join(abs_dir, vt), encoding="utf-8") as f:
            content = f.read()
        vacuous_tests.extend(_detect_vacuous_tests(content, workspace_modules))

    evidence_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "workspace_dir": abs_dir,
        "test_suite": test_suite_data,
        "type_checker": type_checker_data,
        "linter": linter_data,
        "test_provenance": test_provenance,
        "vacuous_tests": vacuous_tests,
        "test_tampering": test_tampering,
        "probe_coverage": probe_coverage,
        "challenge_manifest": {
            "expected_challenges": expected_challenges,
            "missing_challenges": missing_challenges,
            "file_tampered": sandbox_res["file_tampered"],
        },
    }

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(evidence_data, f, indent=2)

    return evidence_data

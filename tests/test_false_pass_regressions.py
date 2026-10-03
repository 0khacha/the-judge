"""Regression tests for confirmed false-PASS bugs.

These tests ensure that the following scenarios never silently produce DECISION: PASS:

  P1 — always-raising function / always-failing constructor
  P2 — critical requirement with zero matching implementation logic
  P3 — conftest.py collection hijack with no judge.json contract
"""

import ast
import os
import sys
import tempfile
import textwrap

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_workspace(files: dict) -> str:
    """Create a temporary directory with the given {filename: content} mapping."""
    tmp = tempfile.mkdtemp()
    for name, content in files.items():
        path = os.path.join(tmp, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(textwrap.dedent(content))
    return tmp


# ---------------------------------------------------------------------------
# Priority 1 — Swallowed exceptions → false PASS
# ---------------------------------------------------------------------------


class TestP1SwallowedExceptions:
    """An always-raising function or class must not produce DECISION: PASS."""

    def test_always_raising_function_is_not_pass(self):
        """Function that raises RuntimeError on every call must not result in PASS."""
        workspace = _write_workspace(
            {
                "broken.py": """
                    def normalize(text: str) -> str:
                        raise RuntimeError("Totally broken - always crashes on any input")
                """
            }
        )
        from the_judge.api import verify

        result = verify(workspace)
        assert result.decision != "PASS", (
            f"Always-raising function produced {result.decision} (score={result.numeric_score}), "
            "expected FAIL or ABSTAIN. This is the P1 false-PASS regression."
        )

    def test_always_raising_class_constructor_is_not_pass(self):
        """Class whose __init__ always raises must not result in PASS."""
        workspace = _write_workspace(
            {
                "broken2.py": """
                    class DataProcessor:
                        def __init__(self):
                            raise ValueError("Cannot construct this class - always fails")
                        def process(self, x):
                            return x
                """
            }
        )
        from the_judge.api import verify

        result = verify(workspace)
        assert result.decision != "PASS", (
            f"Always-raising constructor produced {result.decision} (score={result.numeric_score}), "
            "expected FAIL or ABSTAIN. This is the P1 false-PASS regression."
        )

    def test_generated_idempotency_probe_code_does_not_swallow_runtime_errors(self):
        """The generated idempotency probe code must only catch TypeError, not RuntimeError."""
        from the_judge.core.behavior_engine import BehaviorEngine

        workspace = _write_workspace(
            {
                "crasher.py": """
                    def normalize(text: str) -> str:
                        raise RuntimeError("always crashes")
                """
            }
        )
        engine = BehaviorEngine()
        probes = engine.generate_behavioral_probes(workspace)
        assert probes, "Expected at least one probe to be generated for crasher.py"

        for probe in probes:
            code = probe.executable_code
            # The probe must NOT have a bare "except Exception: pass" that hides all crashes
            assert "except Exception:\n        pass" not in code, (
                f"Probe '{probe.property_kind}' for '{probe.target_symbol}' contains bare "
                "'except Exception: pass' which silently swallows crashes. "
                "Only TypeError should be caught."
            )
            # Verify the generated code is valid Python
            try:
                ast.parse(code)
            except SyntaxError as e:
                pytest.fail(f"Generated probe code has syntax error: {e}\n\nCode:\n{code}")

    def test_generated_state_isolation_probe_code_does_not_swallow_value_errors(self):
        """The generated state-isolation probe must only catch TypeError."""
        from the_judge.core.behavior_engine import BehaviorEngine

        workspace = _write_workspace(
            {
                "broken_class.py": """
                    class BadClass:
                        def __init__(self):
                            raise ValueError("always broken")
                        def run(self):
                            pass
                """
            }
        )
        engine = BehaviorEngine()
        probes = engine.generate_behavioral_probes(workspace)
        assert probes, "Expected at least one probe for BadClass"

        for probe in probes:
            code = probe.executable_code
            assert "except Exception:\n        pass" not in code, (
                f"State-isolation probe contains bare 'except Exception: pass' which "
                "would hide a ValueError from a broken constructor."
            )


# ---------------------------------------------------------------------------
# Priority 2 — Critical requirement with no enforcement logic → ABSTAIN
# ---------------------------------------------------------------------------


class TestP2CriticalRequirementCoverage:
    """A critical requirement with no matching structural evidence must be ABSTAIN, not PASS."""

    def test_critical_requirement_no_matching_logic_is_abstain(self):
        """
        charge_card() always returns True with no validation logic.
        REQ-001 requires amount validation. No test or structural pattern matches.
        Expected: ABSTAIN (not PASS).
        """
        import json

        workspace = _write_workspace(
            {
                "payment.py": """
                    def charge_card(amount: float, card_token: str) -> bool:
                        return True  # no validation logic at all
                """,
                "judge.json": json.dumps(
                    {
                        "name": "payment-service",
                        "requirements": [
                            {
                                "id": "REQ-001",
                                "description": "Must reject negative or zero payment amounts",
                                "category": "boundary",
                                "priority": "critical",
                                "properties": ["amount_validation"],
                            }
                        ],
                    }
                ),
            }
        )

        import json as _json

        spec_path = os.path.join(workspace, "judge.json")
        with open(spec_path, encoding="utf-8") as f:
            task_spec = _json.load(f)

        from the_judge.api import verify

        result = verify(workspace, task_spec=task_spec)
        assert result.decision != "PASS", (
            f"Critical requirement with no matching implementation produced DECISION: PASS "
            f"(score={result.numeric_score}). Expected ABSTAIN."
        )

    def test_trivial_existence_test_is_not_generated_for_requirements(self):
        """
        generate_property_tests() must NOT produce a trivially-passing test that just
        checks 'module exports at least one symbol' for a contract requirement.
        Such tests provide zero evidence that the requirement is actually implemented.
        """
        import json

        workspace = _write_workspace(
            {
                "payment.py": "def charge_card(amount, card_token): return True\n",
                "judge.json": json.dumps(
                    {
                        "name": "payment-service",
                        "requirements": [
                            {
                                "id": "REQ-001",
                                "description": "Must reject negative amounts",
                                "priority": "critical",
                                "properties": ["amount_validation"],
                            }
                        ],
                    }
                ),
            }
        )
        import json as _json

        with open(os.path.join(workspace, "judge.json"), encoding="utf-8") as f:
            task_spec = _json.load(f)

        from the_judge.core.property_engine import generate_property_tests

        candidates = generate_property_tests(workspace, task_spec=task_spec)

        trivial_tests = [
            c
            for c in candidates
            if "must export at least one symbol" in c.challenge_code
            or "public_objs" in c.challenge_code
        ]
        assert trivial_tests == [], (
            f"generate_property_tests produced {len(trivial_tests)} trivially-passing "
            "existence test(s) for contract requirements. These falsely mark requirements "
            "as VERIFIED without exercising any described behaviour:\n"
            + "\n".join(c.challenge_code[:200] for c in trivial_tests)
        )

    def test_contract_engine_unverified_critical_blocks_pass(self):
        """
        When a critical requirement has no matching test evidence, the ContractEngine
        must report it as UNVERIFIED, and the score_engine must then produce ABSTAIN.
        """
        from the_judge.core.contract_engine import ContractEngine
        from the_judge.core.score_engine import evaluate

        spec = {
            "requirements": [
                {
                    "id": "REQ-001",
                    "description": "Must reject negative or zero payment amounts",
                    "category": "boundary",
                    "priority": "critical",
                    "properties": ["amount_validation"],
                }
            ]
        }
        engine = ContractEngine(task_spec=spec)

        # No test evidence at all for this requirement
        ground_truth = {
            "test_suite": {"exit_code": 0, "passed_tests": [], "failed_tests": []},
            "test_provenance": {},
        }
        findings = {"requirements": [], "security_notes": []}

        coverage = engine.evaluate_contract_coverage(ground_truth, findings)
        assert "REQ-001" in coverage["summary"]["critical_unverified_ids"], (
            "REQ-001 with no test evidence must appear in critical_unverified_ids"
        )

        # Now feed into the score_engine — should ABSTAIN
        ground_truth["contract_data"] = coverage
        result = evaluate(findings, ground_truth)
        assert result["verdict"] != "PASS", (
            f"Score engine produced PASS despite unverified critical requirement. "
            f"Got verdict={result['verdict']}"
        )


# ---------------------------------------------------------------------------
# Priority 3 — Collection hijack with no judge.json → FAIL, not PASS
# ---------------------------------------------------------------------------


class TestP3CollectionTamperingNoContract:
    """conftest.py collection hijack must be detected in no-contract (no judge.json) mode."""

    def test_conftest_collection_hijack_detected_without_contract(self):
        """
        A conftest.py that silently drops a test from collection must NOT produce PASS.
        This is the P3 regression: in ad-hoc mode (no judge.json) the missing test
        must be detected via the AST-based expected_challenges manifest.
        """
        workspace = _write_workspace(
            {
                "mod.py": """
                    def broken(x: int) -> int:
                        return x - 999999
                """,
                "test_mod.py": """
                    from mod import broken
                    def test_broken_correctness():
                        assert broken(5) == 5
                """,
                "_hidden_hijack.py": """
                    def pytest_collection_modifyitems(config, items):
                        items[:] = [i for i in items if "broken_correctness" not in i.name]
                """,
                "conftest.py": "from _hidden_hijack import pytest_collection_modifyitems  # noqa: F401\n",
            }
        )

        from the_judge.api import verify

        result = verify(workspace)
        assert result.decision != "PASS", (
            f"Collection hijack produced DECISION: PASS (score={result.numeric_score}). "
            "test_broken_correctness was silently dropped by conftest.py but the judge "
            "should detect it as a missing challenge and produce FAIL or ABSTAIN."
        )

    def test_visible_test_functions_added_to_expected_challenges(self):
        """
        After the P3 fix, visible test file function names must appear in expected_challenges
        so the manifest comparison can catch missing tests.
        """
        workspace = _write_workspace(
            {
                "mod.py": "def add(a, b): return a + b\n",
                "test_mod.py": textwrap.dedent("""
                    from mod import add
                    def test_add_positive():
                        assert add(1, 2) == 3
                    def test_add_negative():
                        assert add(-1, -1) == -2
                """),
            }
        )

        # Directly test the evidence capture manifest
        from the_judge.core.property_engine import generate_property_tests
        from the_judge.core.behavior_engine import BehaviorEngine

        # Simulate what capture_evidence does when building expected_challenges
        abs_dir = os.path.abspath(workspace)
        candidates = generate_property_tests(abs_dir)
        beh_engine = BehaviorEngine()
        probes = beh_engine.generate_behavioral_probes(abs_dir)

        expected_challenges = []
        for cand in candidates:
            for line in cand.challenge_code.splitlines():
                if line.strip().startswith("def test_"):
                    fn_name = line.strip().split("(")[0].replace("def ", "").strip()
                    expected_challenges.append(fn_name)
        for probe in probes:
            for line in probe.executable_code.splitlines():
                if line.strip().startswith("def test_"):
                    fn_name = line.strip().split("(")[0].replace("def ", "").strip()
                    expected_challenges.append(fn_name)

        # Simulate the P3 fix: AST-parse visible test files
        import ast as _ast
        visible_tests = [f for f in os.listdir(abs_dir) if f.startswith("test_") and f.endswith(".py")]
        for vt in visible_tests:
            with open(os.path.join(abs_dir, vt), encoding="utf-8") as f:
                content = f.read()
            try:
                tree = _ast.parse(content, filename=vt)
                for node in _ast.walk(tree):
                    if isinstance(node, _ast.FunctionDef) and node.name.startswith("test_"):
                        if node.name not in expected_challenges:
                            expected_challenges.append(node.name)
            except Exception:
                pass

        assert "test_add_positive" in expected_challenges, (
            "test_add_positive from visible test_mod.py not in expected_challenges"
        )
        assert "test_add_negative" in expected_challenges, (
            "test_add_negative from visible test_mod.py not in expected_challenges"
        )


# ---------------------------------------------------------------------------
# Priority 4 — Probe scope / documentation (unit assertion on probe behaviour)
# ---------------------------------------------------------------------------


class TestP4ProbeScope:
    """Document and assert the known limitations of auto-generated probes."""

    def test_numeric_function_wrong_return_gets_variance_probe(self):
        """
        Bug 1 fix: A purely numeric function (int→int) with a completely wrong
        return value now gets a multi-input variance probe that catches the defect.

        Previously (known limitation): 2-param functions got no meaningful probe.
        Now: the multi-input variance probe calls with varied inputs and asserts
        outputs are not all identical, catching hardcoded/constant returns.
        """
        workspace = _write_workspace(
            {
                "adder.py": """
                    def add(a: int, b: int) -> int:
                        return 0  # always wrong
                """
            }
        )
        from the_judge.core.behavior_engine import BehaviorEngine

        engine = BehaviorEngine()
        probes = engine.generate_behavioral_probes(workspace)

        add_probes = [p for p in probes if p.target_symbol == "add"]
        # With the Bug 1 fix, add() should get at least a variance probe
        variance_probes = [p for p in add_probes if "multi_input" in p.property_kind]
        assert len(variance_probes) > 0, (
            "Bug 1 fix: add(a, b) should now get a multi-input variance probe."
        )
        # The variance probe should have an assertion that checks output diversity
        for vp in variance_probes:
            assert "unique_count" in vp.executable_code or "unique" in vp.executable_code, (
                "Variance probe should check for output uniqueness across inputs."
            )


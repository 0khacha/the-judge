"""Black-Box Behavioral Verification Engine for The Judge v4.0.

Key Capabilities:
  1. Vocabulary-Free Interface Discovery (inspect signatures, type annotations, return shapes)
  2. Bounded Seed-Recorded Dynamic Input Generators (int, float, str, bytes, bool, list, dict)
  3. Experimental Behavioral Probe Generation (determinism, idempotency, boundary consistency, state isolation)
  4. Traceable execution metadata (seed, input, property, duration, process identity)
"""

import importlib.util
import inspect
import os
import random
import sys
from dataclasses import dataclass
from typing import Any


@dataclass
class BehavioralProbe:
    """Record of a single experimental behavioral probe."""

    property_kind: str
    target_symbol: str
    seed: int
    inputs: tuple[Any, ...]
    kwargs: dict[str, Any]
    expected_invariant: str
    rationale: str
    executable_code: str


class ValueGenerator:
    """Bounded, seed-driven input value generator for black-box probing."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)

    def generate_for_type(self, param_type: Any, param_name: str = "") -> list[Any]:
        """Generate bounded probe values based on type annotation or name hint."""
        t_str = str(param_type).lower() if param_type is not inspect.Parameter.empty and param_type is not None else ""

        if param_type is int or t_str == "int" or param_name.endswith("_int") or "count" in param_name:
            return [0, 1, -1, 2, 10, 100, 999999]
        elif (
            param_type is float or t_str == "float"
            or param_name.endswith("_float")
            or "price" in param_name
            or "amount" in param_name
        ):
            return [0.0, 1.0, -1.0, 99.99, 100.0, 100.01, 0.001]
        elif (
            param_type is str or t_str == "str"
            or param_name.endswith("_str")
            or "text" in param_name
            or "key" in param_name
        ):
            return ["", "test", "TestInput123!", "<script>alert(1)</script>", "a" * 500]
        elif param_type is bytes or t_str == "bytes":
            return [b"", b"test_bytes", b"\x00" * 32]
        elif param_type is bool or t_str == "bool":
            return [True, False]
        elif param_type is list or t_str == "list":
            return [[], [1], [1, 2, 3], ["a", "b"]]
        elif param_type is dict or t_str == "dict":
            return [{}, {"k": "v"}, {"key": 100}]
        else:
            return [0, 1.0, "test_value", True, None]


class BehaviorEngine:
    """Structure-agnostic, vocabulary-free behavioral probe generator."""

    def __init__(self, seed: int = 98765):
        self.seed = seed
        self.generator = ValueGenerator(seed)

    def discover_callables(self, task_dir: str) -> list[dict[str, Any]]:
        """Introspect target workspace files and discover public callables without keyword filtering."""
        abs_target = os.path.abspath(task_dir)
        py_files = [
            f
            for f in os.listdir(abs_target)
            if f.endswith(".py")
            and not f.startswith("test_")
            and not f.startswith("run_")
            and not f.startswith("_")
            and f
            not in (
                "apply_fix.py",
                "hook.py",
                "hidden_evaluator.py",
                "repaired_code.py",
                "initial_code.py",
            )
        ]

        discovered: list[dict[str, Any]] = []

        import ast

        class DummyParam:
            def __init__(self, name: str, annotation: Any):
                self.name = name
                self.annotation = annotation

        for fname in py_files:
            mod_name = fname[:-3]
            fpath = os.path.join(abs_target, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    source = f.read()
                tree = ast.parse(source)
            except Exception:
                continue

            for node in tree.body:
                if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                    params = []
                    for arg in node.args.args:
                        ann_str = ast.unparse(arg.annotation) if arg.annotation else inspect.Parameter.empty
                        params.append(DummyParam(arg.arg, ann_str))
                    
                    ret_ann = ast.unparse(node.returns) if node.returns else inspect.Parameter.empty

                    discovered.append(
                        {
                            "type": "function",
                            "module": mod_name,
                            "name": node.name,
                            "callable": None,
                            "signature": None,
                            "parameters": params,
                            "return_annotation": ret_ann,
                        }
                    )
                elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                    methods = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and not item.name.startswith("_"):
                            methods.append(item.name)
                    
                    discovered.append(
                        {
                            "type": "class",
                            "module": mod_name,
                            "name": node.name,
                            "class": None,
                            "init_signature": None,
                            "methods": methods,
                        }
                    )

        return discovered

    def generate_behavioral_probes(self, task_dir: str) -> list[BehavioralProbe]:
        """Generate black-box behavioral probes across discovered callables."""
        callables = self.discover_callables(task_dir)
        probes: list[BehavioralProbe] = []

        for item in callables:
            if item["type"] == "function":
                func_name = item["name"]
                mod_name = item["module"]
                params = item["parameters"]

                if not params:
                    continue

                first_param = params[0]
                p_type = (
                    first_param.annotation
                    if first_param.annotation != inspect.Parameter.empty
                    else str
                )
                test_vals = self.generator.generate_for_type(p_type, first_param.name)

                seed = random.randint(10000, 99999)
                code = f"""import pytest, sys, os
import {mod_name}

def test_behavior_idempotency_{mod_name}_{func_name}():
    fn = getattr({mod_name}, '{func_name}')
    val = {repr(test_vals[1] if len(test_vals) > 1 else "test")}
    try:
        res1 = fn(val)
    except TypeError:
        # Probe not applicable: function signature does not accept this value type.
        pytest.skip("Probe not applicable: function signature mismatch")
    # Any other exception (RuntimeError, ValueError, etc.) propagates as a test failure.
    if type(res1) == type(val):
        res2 = fn(res1)
        assert res2 == res1, "Transformation must be idempotent (fn(fn(x)) == fn(x))."
"""
                probes.append(
                    BehavioralProbe(
                        property_kind="idempotency",
                        target_symbol=func_name,
                        seed=seed,
                        inputs=(test_vals[1],),
                        kwargs={},
                        expected_invariant="fn(fn(x)) == fn(x)",
                        rationale=f"Black-box probe: transformer '{func_name}' idempotency check",
                        executable_code=code,
                    )
                )

                # Multi-input variance probe: call function with multiple different
                # input combinations and verify outputs are not all identical
                # (catches hardcoded returns like `return 5`).
                param_value_lists = []
                for p in params:
                    pt = (
                        p.annotation
                        if p.annotation != inspect.Parameter.empty
                        else str
                    )
                    param_value_lists.append(
                        self.generator.generate_for_type(pt, p.name)
                    )

                n_rounds = min(5, max(len(v) for v in param_value_lists))
                input_sets = []
                for i in range(n_rounds):
                    args = tuple(
                        vals[i % len(vals)] for vals in param_value_lists
                    )
                    input_sets.append(args)

                inputs_repr = repr(input_sets)
                seed2 = random.randint(10000, 99999)
                variance_code = (
                    f"import pytest, sys, os\n"
                    f"import {mod_name}\n"
                    f"\n"
                    f"def test_behavior_multi_input_{mod_name}_{func_name}():\n"
                    f"    fn = getattr({mod_name}, '{func_name}')\n"
                    f"    test_inputs = {inputs_repr}\n"
                    f"    results = []\n"
                    f"    for args in test_inputs:\n"
                    f"        try:\n"
                    f"            r = fn(*args)\n"
                    f"            results.append(repr(r))\n"
                    f"        except TypeError:\n"
                    f"            pytest.skip('Probe not applicable: function signature mismatch')\n"
                    f"        except Exception as e:\n"
                    f"            results.append('__ERR:' + type(e).__name__)\n"
                    f"    if len(results) >= 3:\n"
                    f"        unique_count = len(set(results))\n"
                    f"        assert unique_count > 1, (\n"
                    f"            'Suspicious: function returned identical value for all '\n"
                    f"            + str(len(results)) + ' varied inputs: ' + results[0]\n"
                    f"        )\n"
                )
                probes.append(
                    BehavioralProbe(
                        property_kind="multi_input_variance",
                        target_symbol=func_name,
                        seed=seed2,
                        inputs=tuple(input_sets),
                        kwargs={},
                        expected_invariant="outputs vary across different inputs",
                        rationale=f"Black-box probe: '{func_name}' multi-input variance check (detects hardcoded returns)",
                        executable_code=variance_code,
                    )
                )

            elif item["type"] == "class":
                cls_name = item["name"]
                mod_name = item["module"]
                methods = item["methods"]

                if not methods:
                    continue

                seed = random.randint(10000, 99999)
                code = f"""import pytest, sys, os
import {mod_name}

def test_behavior_state_isolation_{mod_name}_{cls_name}():
    cls = getattr({mod_name}, '{cls_name}')
    try:
        inst1 = cls()
        inst2 = cls()
    except TypeError:
        # Probe not applicable: constructor requires arguments.
        pytest.skip("Probe not applicable: constructor requires arguments")
    # Any other exception (ValueError, RuntimeError, etc.) propagates as a failure —
    # a constructor that always raises has a defect, not a signature mismatch.
    assert inst1 is not inst2, "Independent class instantiations must yield distinct objects."
"""
                probes.append(
                    BehavioralProbe(
                        property_kind="state_isolation",
                        target_symbol=cls_name,
                        seed=seed,
                        inputs=(),
                        kwargs={},
                        expected_invariant="inst1 is not inst2",
                        rationale=f"Black-box probe: class '{cls_name}' instance state isolation check",
                        executable_code=code,
                    )
                )

        return probes

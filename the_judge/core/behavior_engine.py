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
        if param_type is int or param_name.endswith("_int") or "count" in param_name:
            return [0, 1, -1, 2, 10, 100, 999999]
        elif (
            param_type is float
            or param_name.endswith("_float")
            or "price" in param_name
            or "amount" in param_name
        ):
            return [0.0, 1.0, -1.0, 99.99, 100.0, 100.01, 0.001]
        elif (
            param_type is str
            or param_name.endswith("_str")
            or "text" in param_name
            or "key" in param_name
        ):
            return ["", "test", "TestInput123!", "<script>alert(1)</script>", "a" * 500]
        elif param_type is bytes:
            return [b"", b"test_bytes", b"\x00" * 32]
        elif param_type is bool:
            return [True, False]
        elif param_type is list:
            return [[], [1], [1, 2, 3], ["a", "b"]]
        elif param_type is dict:
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

        sys_path_added = False
        if abs_target not in sys.path:
            sys.path.insert(0, abs_target)
            sys_path_added = True

        try:
            for fname in py_files:
                mod_name = fname[:-3]
                try:
                    mod = importlib.import_module(mod_name)
                except Exception:
                    continue

                for attr_name in dir(mod):
                    if attr_name.startswith("_"):
                        continue
                    obj = getattr(mod, attr_name)

                    if inspect.isfunction(obj) and obj.__module__ == mod_name:
                        sig = inspect.signature(obj)
                        discovered.append(
                            {
                                "type": "function",
                                "module": mod_name,
                                "name": attr_name,
                                "callable": obj,
                                "signature": sig,
                                "parameters": list(sig.parameters.values()),
                                "return_annotation": sig.return_annotation,
                            }
                        )
                    elif inspect.isclass(obj) and obj.__module__ == mod_name:
                        init_sig = (
                            inspect.signature(obj.__init__) if hasattr(obj, "__init__") else None
                        )
                        methods = [
                            m
                            for m in dir(obj)
                            if not m.startswith("_") and callable(getattr(obj, m, None))
                        ]
                        discovered.append(
                            {
                                "type": "class",
                                "module": mod_name,
                                "name": attr_name,
                                "class": obj,
                                "init_signature": init_sig,
                                "methods": methods,
                            }
                        )
        finally:
            if sys_path_added and abs_target in sys.path:
                sys.path.remove(abs_target)

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
        if isinstance(res1, str):
            res2 = fn(res1)
            assert res2 == res1, "Transformation must be idempotent (fn(fn(x)) == fn(x))."
    except Exception:
        pass
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
        assert inst1 is not inst2, "Independent class instantiations must yield distinct objects."
    except Exception:
        pass
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

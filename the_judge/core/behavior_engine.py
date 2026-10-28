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
        """Generate black-box behavioral probes across discovered callables.

        Returns no probes. The generic probes this engine used to emit were unsound:
          * function idempotency (fn(fn(x)) == fn(x)) and multi-input variance
            ("outputs must differ") assert properties correct functions need not
            have, so they failed correct code (P0-1);
          * class state isolation (Cls() is not Cls()) holds for every ordinary
            class, so it could never fail and only padded "independent evidence"
            (P1-5).
        Contract-shaped probes live in property_engine; discover_callables() is kept
        for callers that inspect a workspace's interface.
        """
        del task_dir
        return []

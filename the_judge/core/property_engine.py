"""Structure-driven behavioral property inference engine."""

import ast
import os
import random
from dataclasses import dataclass
from typing import Any, Optional

# Shared helpers emitted at the top of every generated probe. Probes invent their
# inputs, so an exception raised on those inputs means "probe not applicable" (skip),
# never "defect found". Only the probe's explicit assertions can fail it.
_PROBE_PRELUDE = '''import inspect
import pytest


def _construct(cls, overrides):
    """Instantiate cls, passing only `overrides`; skip if another required arg exists."""
    try:
        sig = inspect.signature(cls)
    except (TypeError, ValueError):
        pytest.skip("probe not applicable: constructor signature unavailable")
    kwargs = {}
    for name, p in sig.parameters.items():
        if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            continue
        if name in overrides:
            kwargs[name] = overrides[name]
        elif p.default is p.empty:
            pytest.skip(f"probe not applicable: cannot satisfy required argument {name!r}")
    try:
        return cls(**kwargs)
    except Exception as exc:
        pytest.skip(f"probe not applicable: constructor raised {type(exc).__name__}")


def _call(fn, *args, **kwargs):
    """Call fn on probe-invented input; any exception means the probe does not apply."""
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        pytest.skip(f"probe not applicable: {getattr(fn, '__name__', fn)} raised {type(exc).__name__}")
'''


@dataclass
class PropertyCandidate:
    kind: str  # "boundary", "rollback_isolation", "uniqueness", "expiration", "idempotency"
    confidence: str  # "HIGH", "MEDIUM", "LOW"
    numeric_confidence: float
    rationale: str
    source_module: str
    source_symbol: str
    ast_nodes: list[str]
    seed: int
    challenge_code: str


class StructurePropertyEngine:
    """Structure-driven behavioral property inference engine."""

    def __init__(self, seed: int = 48127):
        self.seed = seed
        random.seed(seed)

    def analyze_module_ast(self, filepath: str, mod_name: str) -> list[PropertyCandidate]:
        candidates: list[PropertyCandidate] = []
        try:
            with open(filepath, encoding="utf-8") as f:
                content = f.read()
            tree = ast.parse(content, filename=filepath)
        except Exception:
            return candidates

        # Boundary-perturbation and uniqueness probes were removed: neither had an
        # oracle for correct behaviour (a function near a threshold may legitimately
        # return None or raise; a digest is deterministic by design), so they failed
        # correct code without detecting real defects.
        rollback_candidates = self._infer_rollback_candidates(tree, content, mod_name)
        candidates.extend(rollback_candidates)

        expiration_candidates = self._infer_expiration_candidates(tree, content, mod_name)
        candidates.extend(expiration_candidates)

        capacity_candidates = self._infer_capacity_candidates(tree, content, mod_name)
        candidates.extend(capacity_candidates)

        idempotency_candidates = self._infer_idempotency_candidates(tree, content, mod_name)
        candidates.extend(idempotency_candidates)

        return [c for c in candidates if c.confidence in ("HIGH", "MEDIUM")]

    def _infer_rollback_candidates(
        self, tree: ast.AST, content: str, mod_name: str
    ) -> list[PropertyCandidate]:
        candidates: list[PropertyCandidate] = []
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]

        for cls in classes:
            method_names = [m.name for m in cls.body if isinstance(m, ast.FunctionDef)]
            has_checkpoint = any(
                m in ("begin", "start", "checkpoint", "start_journal", "savepoint")
                for m in method_names
            )
            has_revert = any(
                m in ("rollback", "revert", "abort", "revert_journal", "undo") for m in method_names
            )

            # The probe needs real methods to call: a checkpoint, a revert, a writer
            # and a reader. Without all four it could not assert anything, so it is
            # not emitted (module text mentioning "transaction" is not enough).
            set_name = next((m for m in ("set", "put", "write") if m in method_names), None)
            get_name = next((m for m in ("get", "read") if m in method_names), None)
            if has_checkpoint and has_revert and set_name and get_name:
                seed = random.randint(10000, 99999)
                cp_name = next(
                    m for m in method_names
                    if m in ("begin", "start", "checkpoint", "start_journal", "savepoint")
                )
                rv_name = next(
                    m for m in method_names
                    if m in ("rollback", "revert", "abort", "revert_journal", "undo")
                )

                candidates.append(
                    PropertyCandidate(
                        kind="rollback_isolation",
                        confidence="HIGH",
                        numeric_confidence=0.92,
                        rationale=f"Class '{cls.name}' exhibits state mutation with checkpoint ({cp_name}) and revert ({rv_name}) operations.",
                        source_module=mod_name,
                        source_symbol=cls.name,
                        ast_nodes=[cls.name],
                        seed=seed,
                        challenge_code=_PROBE_PRELUDE + f"""
import {mod_name}

def test_prop_rollback_isolation_{mod_name}_{cls.name}():
    cls = getattr({mod_name}, '{cls.name}')
    inst = _construct(cls, {{}})

    _call(inst.{set_name}, "existing_k", 100)
    _call(inst.{cp_name})
    _call(inst.{set_name}, "uncommitted_k", 999)
    _call(inst.{rv_name})

    val_existing = _call(inst.{get_name}, "existing_k")
    try:
        val_uncommitted = inst.{get_name}("uncommitted_k")
    except LookupError:
        val_uncommitted = None  # raising KeyError for an absent key is fine

    assert val_existing == 100, "State written before the checkpoint must survive rollback."
    assert val_uncommitted != 999, "A write made after the checkpoint must be undone by rollback."
""",
                    )
                )

        return candidates

    # Trigger vocabulary (heuristic, keyword based; see README "Known Limitations").
    _TTL_PARAMS = ("ttl", "ttl_seconds", "expire", "expiry")
    _CAPACITY_PARAMS = ("capacity", "max_size", "limit", "bound")
    _PUT_METHODS = ("put", "set", "write", "store", "add", "store_session", "insert")
    _GET_METHODS = ("get", "read", "lookup", "fetch", "fetch_session")

    @staticmethod
    def _uses_controllable_clock(tree: ast.AST) -> bool:
        """True if the module reads time only via time.time / time.monotonic.

        The expiration probe advances time by patching those two functions, so it
        must not run on code whose clock it cannot control (datetime, perf_counter,
        *_ns variants, ...): such code would keep a correct entry alive and fail.
        """
        controllable = {"time", "monotonic"}
        uses = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                if node.value.id == "time":
                    if node.attr in controllable:
                        uses = True
                    elif node.attr not in ("sleep",):
                        return False
            elif isinstance(node, ast.ImportFrom) and node.module == "time":
                for alias in node.names:
                    if alias.name in controllable:
                        uses = True
                    elif alias.name != "sleep":
                        return False
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                if any(n.split(".")[0] == "datetime" for n in names):
                    return False
        return uses

    def _infer_expiration_candidates(
        self, tree: ast.AST, content: str, mod_name: str
    ) -> list[PropertyCandidate]:
        candidates: list[PropertyCandidate] = []
        if not self._uses_controllable_clock(tree):
            return candidates
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]

        for cls in classes:
            init_fn = [
                m for m in cls.body if isinstance(m, ast.FunctionDef) and m.name == "__init__"
            ]
            if not init_fn:
                continue

            init_args = [a.arg for a in init_fn[0].args.args]
            ttl_param = next((a for a in init_args if a in self._TTL_PARAMS), None)
            cap_params = [a for a in init_args if a in self._CAPACITY_PARAMS]

            method_names = [m.name for m in cls.body if isinstance(m, ast.FunctionDef)]
            put_names = [m for m in method_names if m in self._PUT_METHODS]
            get_names = [m for m in method_names if m in self._GET_METHODS]

            if ttl_param and put_names and get_names:
                seed = random.randint(10000, 99999)
                get_name = get_names[0]
                put_name = put_names[0]
                overrides = {ttl_param: 1}
                overrides.update(dict.fromkeys(cap_params, 1000))

                candidates.append(
                    PropertyCandidate(
                        kind="expiration",
                        confidence="HIGH",
                        numeric_confidence=0.91,
                        rationale=f"Class '{cls.name}' accepts time/expiry parameter in __init__; entries past expiration must not be observable.",
                        source_module=mod_name,
                        source_symbol=cls.name,
                        ast_nodes=[cls.name],
                        seed=seed,
                        challenge_code=_PROBE_PRELUDE + f"""
import time
import {mod_name}

_TIME_PARAMS = ("current_time", "now", "timestamp")


def test_prop_expiration_{mod_name}_{cls.name}(monkeypatch):
    # ttl=1 in whatever unit the class uses; then advance the clock by 1e7 seconds
    # (~115 days), which is past expiry for second, millisecond, minute, hour or day
    # units. Time is advanced by patching time.time/time.monotonic and by passing the
    # same fake clock to any constructor parameter that defaults to one of them.
    real_time, real_mono = time.time, time.monotonic
    offset = [0.0]
    fake_time = lambda: real_time() + offset[0]
    fake_mono = lambda: real_mono() + offset[0]
    monkeypatch.setattr(time, "time", fake_time)
    monkeypatch.setattr(time, "monotonic", fake_mono)
    for attr, real, fake in (("time", real_time, fake_time), ("monotonic", real_mono, fake_mono)):
        if getattr({mod_name}, attr, None) is real:
            monkeypatch.setattr({mod_name}, attr, fake)

    cls = getattr({mod_name}, '{cls.name}')
    overrides = dict({overrides!r})
    for name, p in inspect.signature(cls).parameters.items():
        if p.default is real_time:
            overrides[name] = fake_time
        elif p.default is real_mono:
            overrides[name] = fake_mono
    inst = _construct(cls, overrides)
    put_fn = getattr(inst, '{put_name}')
    get_fn = getattr(inst, '{get_name}')
    put_params = inspect.signature(put_fn).parameters
    get_params = inspect.signature(get_fn).parameters
    if len([n for n in put_params if n not in _TIME_PARAMS]) < 2 or not get_params:
        pytest.skip("probe not applicable: put/get signatures not key-value shaped")

    def at(params, t):
        return {{n: t for n in params if n in _TIME_PARAMS}}

    t0 = fake_time()
    value = object()
    _call(put_fn, "prop_key", value, **at(put_params, t0))
    if _call(get_fn, "prop_key", **at(get_params, t0)) is not value:
        pytest.skip("probe not applicable: stored value not readable back before expiry")

    offset[0] += 1e7
    try:
        res = get_fn("prop_key", **at(get_params, t0 + 1e7))
    except LookupError:
        return  # raising KeyError for an expired key is a valid way to expire it
    assert res is not value, "Entry must not be returned after its time-to-live has elapsed."
""",
                    )
                )

        return candidates

    def _infer_capacity_candidates(
        self, tree: ast.AST, content: str, mod_name: str
    ) -> list[PropertyCandidate]:
        candidates: list[PropertyCandidate] = []
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]

        for cls in classes:
            init_fn = [
                m for m in cls.body if isinstance(m, ast.FunctionDef) and m.name == "__init__"
            ]
            if not init_fn:
                continue

            init_args = [a.arg for a in init_fn[0].args.args]
            has_capacity = any(a in self._CAPACITY_PARAMS for a in init_args)
            overrides: dict[str, Any] = {a: 2 for a in init_args if a in self._CAPACITY_PARAMS}
            # A TTL argument is satisfiable: a long lifetime keeps it out of the way.
            overrides.update({a: 10**6 for a in init_args if a in self._TTL_PARAMS})
            methods = [
                m for m in cls.body if isinstance(m, ast.FunctionDef) and not m.name.startswith("_")
            ]
            method_names = [m.name for m in methods]
            push_names = [
                m
                for m in method_names
                if m in ("push", "add", "enqueue", "consume", "put", "write")
            ]
            # How many items are retained must be observable: via __len__, or via a
            # reader method for keyed containers. Otherwise there is nothing to assert.
            has_len = any(isinstance(m, ast.FunctionDef) and m.name == "__len__" for m in cls.body)
            reader = next((m for m in method_names if m in self._GET_METHODS), None)
            get_name = reader or "get"  # only used on the reader branch below

            if has_capacity and push_names and (has_len or reader):
                seed = random.randint(10000, 99999)
                push_fn = push_names[0]
                candidates.append(
                    PropertyCandidate(
                        kind="capacity_limit",
                        confidence="HIGH",
                        numeric_confidence=0.87,
                        rationale=f"Class '{cls.name}' specifies capacity bound in __init__; pushing items past capacity bound must enforce boundary limits.",
                        source_module=mod_name,
                        source_symbol=cls.name,
                        ast_nodes=[cls.name],
                        seed=seed,
                        challenge_code=_PROBE_PRELUDE + f"""
import {mod_name}

def test_prop_capacity_limit_{mod_name}_{cls.name}():
    cls = getattr({mod_name}, '{cls.name}')
    inst = _construct(cls, {overrides!r})
    p_fn = getattr(inst, '{push_fn}')
    n_args = len([p for p in inspect.signature(p_fn).parameters.values()
                  if p.default is p.empty and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)])
    if n_args not in (1, 2):
        pytest.skip("probe not applicable: insert method is neither item- nor key/value-shaped")
    items = [("cap_key_%d" % i, "cap_value_%d" % i) for i in range(3)]

    def insert(i):
        return p_fn(*items[i][2 - n_args:])

    _call(insert, 0)
    _call(insert, 1)
    try:
        insert(2)
    except Exception:
        rejected = True  # rejecting an item past capacity by raising is acceptable
    else:
        rejected = False

    if {has_len!r}:
        retained = _call(len, inst)
    elif n_args == 2:
        def held(key, value):
            try:
                return inst.{get_name}(key) == value
            except LookupError:
                return False
        retained = sum(held(k, v) for k, v in items)
    else:
        pytest.skip("probe not applicable: cannot observe how many items are retained")

    assert retained <= 2, (
        f"constructed with capacity 2 but {{retained}} items are retained after 3 inserts"
        f" (third insert {{'raised' if rejected else 'returned normally'}})"
    )
""",
                    )
                )

        return candidates

    def _infer_idempotency_candidates(
        self, tree: ast.AST, content: str, mod_name: str
    ) -> list[PropertyCandidate]:
        candidates: list[PropertyCandidate] = []
        # Find top-level functions (not class methods)
        module = tree if isinstance(tree, ast.Module) else None
        if module is None:
            return candidates
        top_level_fns = [n for n in module.body if isinstance(n, ast.FunctionDef)]

        # Name-triggered (heuristic). Only verbs whose contract IS idempotency are
        # listed: encode/escape/parse/format/convert are deliberately excluded because
        # applying them twice legitimately changes the result.
        sanitizer_keywords = ("sanitize", "clean", "strip", "normalize", "purify", "harden")

        for fn in top_level_fns:
            if fn.name.startswith("test_") or fn.name.startswith("_"):
                continue

            args = fn.args.args
            # Only run when the input type is known: exactly one parameter annotated str.
            if len(args) != 1 or args[0].annotation is None:
                continue
            if ast.unparse(args[0].annotation) != "str":
                continue
            if not any(kw in fn.name.lower() for kw in sanitizer_keywords):
                continue

            seed = random.randint(10000, 99999)
            candidates.append(
                PropertyCandidate(
                    kind="idempotency",
                    confidence="MEDIUM",
                    numeric_confidence=0.82,
                    rationale=f"Function '{fn.name}' is a str -> str sanitizer/normalizer; applying it twice must equal applying it once.",
                    source_module=mod_name,
                    source_symbol=fn.name,
                    ast_nodes=[fn.name],
                    seed=seed,
                    challenge_code=_PROBE_PRELUDE + f"""
import {mod_name}

def test_prop_idempotency_{mod_name}_{fn.name}():
    fn = getattr({mod_name}, '{fn.name}')
    probe_inputs = [
        "plain text",
        "  Mixed   Case\\twhitespace  ",
        "<b>hello</b> & <script>alert(1)</script>",
        "(555) 123-4567",
        "../../etc/passwd",
    ]
    pairs = []
    for raw in probe_inputs:
        try:
            once = fn(raw)
            if not isinstance(once, str):
                continue
            pairs.append((raw, once, fn(once)))
        except Exception:
            continue  # rejecting a probe-invented input is not a defect
    if not pairs:
        pytest.skip("probe not applicable: no probe input produced a str result")
    broken = [(raw, once, twice) for raw, once, twice in pairs if twice != once]
    assert not broken, f"{fn.name}(x) must be idempotent; (input, once, twice): {{broken!r}}"
""",
                )
            )

        return candidates


def _probe_target_files(abs_target: str) -> list[str]:
    return sorted(
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
    )


def generate_property_tests(
    task_dir: str, task_spec: Optional[dict[str, Any]] = None
) -> list[PropertyCandidate]:
    abs_target = os.path.abspath(task_dir)
    engine = StructurePropertyEngine(seed=48127)
    candidates: list[PropertyCandidate] = []

    for fname in _probe_target_files(abs_target):
        fpath = os.path.join(abs_target, fname)
        mod_name = fname[:-3]
        mod_candidates = engine.analyze_module_ast(fpath, mod_name)
        candidates.extend(mod_candidates)

        # NOTE: We deliberately do NOT generate trivially-passing existence tests for
        # contract requirements here.  A test that merely checks "the module exports a
        # symbol" provides zero evidence that the described behaviour is actually
        # implemented.  Requirements that have no structural AST evidence (boundary
        # comparisons, rollback patterns, etc.) correctly remain UNVERIFIED, which
        # causes Hard Gate 9 to issue an ABSTAIN — the correct outcome when there is
        # no evidence for a critical requirement.

    return candidates


# What each probe kind needs before it is generated. Triggers are heuristic and
# keyword based: identical logic under other names gets no probe.
PROBE_TRIGGERS: dict[str, str] = {
    "expiration": (
        "class whose __init__ has a parameter named "
        + "/".join(StructurePropertyEngine._TTL_PARAMS)
        + ", with a writer (" + "/".join(StructurePropertyEngine._PUT_METHODS)
        + ") and a reader (" + "/".join(StructurePropertyEngine._GET_METHODS)
        + "), in a module whose clock is time.time/time.monotonic"
    ),
    "capacity_limit": (
        "class whose __init__ has a parameter named "
        + "/".join(StructurePropertyEngine._CAPACITY_PARAMS)
        + ", an insert method (push/add/enqueue/consume/put/write) and __len__ or a reader"
    ),
    "rollback_isolation": (
        "class with begin/start/checkpoint/savepoint, rollback/revert/abort/undo, "
        "set/put/write and get/read methods"
    ),
    "idempotency": (
        "function with one str-annotated parameter whose name contains "
        "sanitize/clean/strip/normalize/purify/harden"
    ),
}


def untriggered_probes(
    task_dir: str, candidates: list[PropertyCandidate]
) -> list[dict[str, str]]:
    """Probe kinds that did not run on each public class/function, and why."""
    abs_target = os.path.abspath(task_dir)
    triggered = {(c.source_module, c.source_symbol, c.kind) for c in candidates}
    out: list[dict[str, str]] = []
    for fname in _probe_target_files(abs_target):
        mod_name = fname[:-3]
        try:
            with open(os.path.join(abs_target, fname), encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                kinds: tuple[str, ...] = ("expiration", "capacity_limit", "rollback_isolation")
            elif isinstance(node, ast.FunctionDef):
                kinds = ("idempotency",)
            else:
                continue
            if node.name.startswith("_"):
                continue
            for kind in kinds:
                if (mod_name, node.name, kind) not in triggered:
                    out.append({
                        "module": mod_name,
                        "symbol": node.name,
                        "kind": kind,
                        "reason": "no keyword trigger matched; this probe runs only for a "
                        + PROBE_TRIGGERS[kind],
                    })
    return out

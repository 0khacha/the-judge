# FIXES.md — Audit Remediation Log

This document tracks all fixes applied to The Judge verification engine
following an independent audit that identified broken or theatrical mechanisms.

---

## P0 — Requirement↔evidence mapping was broken

**File**: `the_judge/api.py` lines 111–149  
**Status**: ✅ FIXED

**Bug**: Two separate issues in the requirement-to-test mapping:
1. `"fail" in t.lower()` matched ANY failed test whose name contained the
   substring "fail" (e.g. `test_failure_message_format`) against ALL requirements.
2. `req_status = "pass" if len(passed_tests) > 0` with `evidence = passed_tests[0]`
   auto-passed every requirement using the first unrelated test as evidence.

**Fix**: Introduced `_matches_requirement(req, test_name)` that matches by
requirement ID and declared `properties` only. Requirements without any matching
test are now marked `"unverified"` instead of auto-passed.

**Regression tests**: `TestRequirementEvidenceMapping` (3 tests)

---

## P0 — "Never trust self-claims" verification was circular

**Files**: `the_judge/api.py`, `the_judge/core/score_engine.py`  
**Status**: ✅ FIXED

**Bug**: The Judge fabricated "agent findings/claims" from its own evidence,
then "cross-checked" them against the same evidence in Hard Gate 5. Both sides
of the comparison came from the Judge itself — circular by construction.

**Fix**: Added `agent_claims` parameter to `verify()`. When external agent
claims are provided, they're used as the input to the discrepancy detector.
When no external claims are provided, Hard Gate 5 (discrepancy check) is
skipped entirely. Added `agent_claims_provided: bool` parameter to
`evaluate()` to control this behavior.

**Regression tests**: `TestSelfClaimsCircularity` (4 tests)

---

## P1 — Target code executed inside the Judge process during discovery

**File**: `the_judge/core/behavior_engine.py`  
**Status**: ✅ FIXED

**Bug**: `discover_callables()` used `importlib.import_module()` and
`getattr()` on target workspace modules, importing untrusted code directly
into the trusted Judge process.

**Fix**: Replaced runtime import with AST-based discovery. `ast.parse()` reads
Python files without executing them and extracts function/class metadata
(names, parameters, annotations) from `FunctionDef` and `ClassDef` nodes.

**Regression tests**: `TestDiscoveryIsolation` (3 tests)

---

## P1 — The "sandbox" was not a sandbox (conftest hijacking)

**File**: `the_judge/core/sandbox.py`  
**Status**: ✅ FIXED

**Bug**: Three issues:
1. Temp dir was created INSIDE the workspace (`os.path.join(abs_task_dir, ...)`),
   allowing workspace `conftest.py` to be auto-loaded by pytest.
2. `inspect.stack` rewriting in the generated conftest was fragile and theatrical.
3. Isolation subdimensions were reported as `"VERIFIED"` for filesystem and import
   isolation when they were only partial.

**Fix**:
1. Temp dir now created via `tempfile.mkdtemp()` — outside the workspace.
   pytest runs from the temp dir, preventing workspace conftest auto-discovery.
2. `inspect.stack` monkey-patching removed entirely. Generated conftest now
   contains only `sys.argv` sanitization and env-var scrubbing.
3. `filesystem_isolation` and `import_isolation` now reported as `"PARTIAL"`.

**Residual risk**: PYTHONPATH still includes the workspace for imports.
Target code could theoretically observe the workspace path. Documented in
THREAT_MODEL.md.

**Regression tests**: `TestSandboxIsolation` (3 tests)

---

## P1 — Dead gates (type checker and linter)

**Files**: `the_judge/core/evidence.py`, `the_judge/core/score_engine.py`  
**Status**: ✅ FIXED

**Bug**: Three dead gates:
1. Type gate only fired when `strict_type_check` was set — nobody ever set it.
2. Missing mypy (`exit_code=-1`) silently disabled type checking.
3. Linter data was hardcoded as `{"exit_code": 0, "error_count": 0}`.

**Fix**:
1. Removed `strict_type_check` guard. Type checker results always evaluated.
2. When mypy unavailable, an insufficient_evidence note is added (ABSTAIN)
   instead of silently passing. `type_checker_data["available"]` flag added.
3. Real linter execution: tries `ruff check .`, falls back to `flake8 .`,
   falls back to `{"available": False}` with an insufficient_evidence note.

**Regression tests**: `TestDeadGates` (3 tests)

---

## P2 — Brittle, spoofable result parsing

**Files**: `the_judge/core/sandbox.py`, `the_judge/core/evidence.py`  
**Status**: ✅ FIXED

**Bug**: Test pass/fail was scraped from stdout lines containing " PASSED"/
" FAILED". Target code printing those strings could pollute results.

**Fix**: Sandbox now runs pytest with `--junitxml=<tmpfile>` and parses the
XML for test results. `parse_pytest_output()` also supports junitxml parsing.
Stdout scraping retained only as a fallback when XML is unavailable.

**Regression tests**: `TestResultParsing` (2 tests)

---

## P2 — Provenance assigned by name substring

**File**: `the_judge/core/evidence.py`  
**Status**: ✅ FIXED

**Bug**: Any test named with `prop_`, `behavior_`, or `req_` was classified as
`judge_challenge_test` with `externally_verified` provenance. Target-authored
tests with those substrings got unearned independence credit.

**Fix**: Provenance is now tracked structurally. The Judge records exactly which
test function names it wrote (from synthesized property tests and behavioral
probes) in a `judge_authored_tests` set. Only tests in that set receive
`judge_challenge_test` provenance.

**Regression tests**: `TestProvenanceStructural` (1 test)

---

## P2 — Tamper detection watches the wrong files

**File**: `the_judge/core/sandbox.py`  
**Status**: ⚠️ DOCUMENTED AS RESIDUAL RISK

**Bug**: Tamper detection only hashes the Judge's synthesized test files, not
the target workspace code. Target code could self-modify during execution.

**Decision**: Since the sandbox temp dir is now outside the workspace and full
workspace hashing has significant performance impact, this is documented as an
explicit residual risk in THREAT_MODEL.md rather than fully mitigated.

---

## P3 — Benchmark integrity

**Status**: ✅ LABELED

**Bug**: The `agent_legacy_simulation/` results directory contained simulated
benchmark data (generated by `TestAgent`, a deterministic harness) without
being clearly labeled as simulated in the directory structure.

**Fix**: Added `SIMULATION_NOTICE.md` to the legacy simulation directory.
The actual benchmark reports already contained methodology disclaimers.
The existing `LEVEL2_AUDIT_REPORT.md` forensic audit explicitly documents
that Level 2 did not run a real LLM agent.

---

## Documentation Updates

- **SECURITY.md**: Added sandbox limitation about workspace conftest (now fixed)
  and clarified that sandbox isolation is subprocess-level with PARTIAL
  filesystem/import isolation.
- **THREAT_MODEL.md**: Added "Target Self-Modification" row documenting
  residual risk. Updated "Identifier Detection" to note inspect.stack rewriting
  was removed.
- **README.md**: Rule 1 ("Never trust self-claims") updated to document that
  external `agent_claims` parameter must be provided for discrepancy detection.

---

## Test Summary

| Category | Tests Added | Status |
|---|---|---|
| P0 Requirement mapping | 3 | ✅ Pass |
| P0 Self-claims circularity | 4 | ✅ Pass |
| P1 Discovery isolation | 3 | ✅ Pass |
| P1 Sandbox isolation | 3 | ✅ Pass |
| P1 Dead gates | 3 | ✅ Pass |
| P2 Result parsing | 2 | ✅ Pass |
| P2 Provenance structural | 1 | ✅ Pass |
| **Total new tests** | **19** | **✅ All pass** |
| **Original tests** | **69** | **✅ All pass** |
| **Full suite** | **88** | **✅ All pass** |

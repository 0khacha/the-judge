"""Turn a verdict into numbered, machine-readable next actions for the agent.

Each action is {"step", "action", "detail"} plus, where useful, "test", "command" and
"guidance". The first action is always the most important one.
"""

from typing import Any, Optional

VERIFY = "judge verify . --json"
FREEZE = "judge freeze ."
MAX_MUTANT_STEPS = 5
MAX_REQUIREMENT_STEPS = 8
REQUIREMENT_GUIDANCE = ("Write a test that checks exactly this rule, including its edge cases, "
                        "and put {rid} in a comment or the docstring of the test. Take the expected "
                        "results from the rule, not from the code. If the test fails, fix the code.")
MUTANT_GUIDANCE = ("Decide the correct behaviour at this line from the task specification "
                   "(not from what the code does now) and add a test that checks it. If the new "
                   "test fails, the code is wrong: fix the code. Do not edit the frozen tests.")
FIX_GUIDANCE = ("Change the implementation so this test passes. Do not edit, skip, "
                "parametrize away or weaken the test.")


class _Steps:
    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []

    def add(self, action: str, detail: str, **extra: Any) -> None:
        item = {"step": len(self.items) + 1, "action": action, "detail": detail}
        item.update({k: v for k, v in extra.items() if v is not None})
        self.items.append(item)


def build(decision: str, eval_output: dict[str, Any], evidence: dict[str, Any],
          loop: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    steps = _Steps()
    notes = eval_output.get("insufficient_evidence_notes", [])
    blocking = eval_output.get("blocking_issues", [])
    suite = evidence.get("test_suite", {})
    independence = evidence.get("independence", {})
    loop = loop or {}

    if loop.get("stuck"):
        steps.add("stop", f"No progress: {loop.get('stuck_reason')}. Stop iterating and report the "
                  "remaining issues listed below to the user.")

    mutation = evidence.get("mutation") or {}
    if decision == "PASS":
        n = len(independence.get("independent", {}))
        caught = (f" The tests caught {mutation['killed']} of {mutation['total']} planted bugs."
                  if mutation.get("ran") else "")
        steps.add("done", f"PASS: all tests passed, including {n} independent test(s) fixed before "
                  f"the implementation.{caught} Report success with numeric_score "
                  f"{eval_output.get('numeric_score')}.")
        return steps.items

    # ---- FAIL ------------------------------------------------------------------------
    tamper = [b for b in blocking if "TAMPERING" in b]
    for issue in tamper:
        steps.add("restore_tests", issue,
                  guidance="Restore the test exactly as it was frozen/committed and fix the code "
                           "instead. If the test itself is wrong, fix it and run `judge freeze .` "
                           "again, and tell the user which test you changed and why.")
    for name in loop.get("regressions", []):
        steps.add("fix_regression", f"{name} passed in the previous verification and fails now.",
                  test=name, guidance=FIX_GUIDANCE)
    errors = suite.get("errors", {})
    already = set(loop.get("regressions", []))
    for name in suite.get("failed_tests", [])[:10]:
        if name in already or not name:
            continue
        steps.add("fix_code", (errors.get(name) or "test failed").strip(), test=name, guidance=FIX_GUIDANCE)
    for issue in blocking:
        if "TAMPERING" in issue or issue.startswith(("Test suite failure", "Requirement failed", "REGRESSION")):
            continue
        steps.add("resolve_blocking", issue)
    if decision == "FAIL":
        if not steps.items:
            steps.add("fix_code", "; ".join(blocking) or "verification failed", guidance=FIX_GUIDANCE)
        steps.add("re_verify", "After the fix, verify again.", command=VERIFY)
        return steps.items

    # ---- ABSTAIN ---------------------------------------------------------------------
    text = " ".join(notes)
    if "(Uncovered Requirements)" in text:
        info = evidence.get("requirements_checklist") or {}
        by_id = {r["id"]: r for r in info.get("requirements", [])}
        for rid in info.get("uncovered", [])[:MAX_REQUIREMENT_STEPS]:
            req = by_id[rid]
            steps.add("cover_requirement", f"{rid} ({req['source']}): \"{req['text']}\" has no "
                      "passing test.", guidance=REQUIREMENT_GUIDANCE.format(rid=rid))
    if "(Weak Tests)" in text:
        for surv in mutation.get("survivors", [])[:MAX_MUTANT_STEPS]:
            steps.add("add_test", f"{surv['file']}:{surv['line']}: changing {surv['change']} in "
                      f"`{surv['code']}` was not detected by any test.",
                      guidance=MUTANT_GUIDANCE)
    if "(Test Runner)" in text:
        steps.add("install_pytest", "pytest could not be started, so no test ran.",
                  command="pip install pytest")
    if "(Timeout)" in text:
        steps.add("raise_timeout", next(n for n in notes if "(Timeout)" in n),
                  command="judge verify . --json --timeout 900",
                  guidance="Raise the limit only if the suite is legitimately slow; a hang "
                           "in the code under test is a bug to fix instead.")
    if "(No Tests)" in text:
        steps.add("write_tests", "No tests were collected. Write test_*.py files with test_* "
                  "functions that assert the behaviour the task specifies (normal cases, edge "
                  "cases, errors).")
        steps.add("freeze_tests", "Freeze those tests BEFORE writing or changing the "
                  "implementation, so they count as independent evidence.", command=FREEZE)
        steps.add("implement", "Write or fix the implementation; do not edit the frozen tests.")
    if "(Skipped Tests)" in text:
        steps.add("unskip_tests", "Skipped/xfail tests prove nothing: " + ", ".join(suite.get("skipped_tests", [])),
                  guidance="Remove the skip/xfail markers and make the tests pass.")
    vacuous = evidence.get("vacuous_tests", [])
    if vacuous:
        steps.add("strengthen_tests", "These tests assert nothing real and are not counted: "
                  + ", ".join(sorted(set(vacuous))),
                  guidance="Assert the concrete expected result of the code under test.")
    if "(Hard-coded Outputs)" in text:
        steps.add("add_tests_other_inputs", next(n for n in notes if "(Hard-coded Outputs)" in n),
                  guidance="Write tests with inputs that do not appear in the implementation's "
                           "literals, freeze them, then make the implementation pass them.",
                  command=FREEZE)
    if "(No Independent Evidence)" in text:
        if independence.get("frozen_after_implementation"):
            detail = ("Tests frozen after the code was written cannot count: they may have been "
                      "fitted to it.")
        else:
            detail = "No passing test was fixed before the implementation."
        steps.add("freeze_tests", detail + " Write tests for the behaviour the task specifies "
                  "(including cases your code does not obviously handle), run `judge freeze .`, "
                  "and only then change the implementation; tests frozen before a code change "
                  "count as independent.", command=FREEZE)
        steps.add("or_user_tests", "Alternatively, ask the user to provide tests and freeze or "
                  "commit them before you change the code (`judge freeze .` or `git commit`).")
        steps.add("or_stop", "If neither is possible, stop: report ABSTAIN and that the code is "
                  "verified only by tests written after it.")
    if "(Coverage-Aware Gate)" in text:
        steps.add("add_named_test", next(n for n in notes if "(Coverage-Aware Gate)" in n),
                  guidance="Add a test whose name contains the requirement id, or list it under "
                           "the requirement's \"tests\" in judge.json.")
    if not steps.items:
        steps.add("investigate", text or "Insufficient evidence.")
    steps.add("re_verify", "Verify again after the step(s) above.", command=VERIFY)
    return steps.items

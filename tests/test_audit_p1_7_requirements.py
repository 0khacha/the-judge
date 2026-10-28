"""P1-7: a judge.json requirement is VERIFIED only by evidence that exercises it.

A `properties` tag that maps to a canned probe (e.g. the single-level rollback
probe) is not evidence that the *described* behaviour ("nested rollback undoes only
the innermost transaction") works. Such a requirement is at most PARTIALLY_VERIFIED,
and a critical requirement that is not VERIFIED makes the verdict ABSTAIN.
A passing workspace test that names the requirement (listed in its `tests`, or
carrying the requirement id in its name) verifies it.
"""

import pytest
from audit_helpers import corpus_workspace, judge, write

TASK = "04_nested_transactions"
NESTED_REQ = {
    "id": "REQ-001",
    "description": "Nested rollback undoes only the innermost transaction",
    "priority": "critical",
    "properties": ["rollback_isolation"],
}
NESTED_TEST = '''
from kvstore import KVStore


def test_nested_rollback_only_inner():
    db = KVStore()
    db.begin()
    db.set("a", 1)
    db.begin()
    db.set("a", 2)
    db.rollback()
    assert db.get("a") == 1
'''


def _coverage(result):
    return result.trust_profile["specification_coverage"]


@pytest.mark.parametrize("variant", ["wrong_rollback_all", "correct"])
def test_tag_mapped_requirement_is_not_verified(tmp_path, variant):
    result = judge(corpus_workspace(tmp_path, TASK, variant), task_spec={"requirements": [NESTED_REQ]})
    cov = _coverage(result)
    req = cov["requirements"][0]
    assert req["status"] in ("PARTIALLY_VERIFIED", "UNVERIFIED"), req
    assert cov["summary"]["overall_coverage_pct"] < 100.0
    assert result.decision != "PASS"
    if variant == "wrong_rollback_all":
        assert "REQ-001" in cov["summary"]["critical_unverified_ids"]


def test_requirement_verified_by_a_named_passing_test(tmp_path):
    ws = corpus_workspace(tmp_path, TASK, "correct", frozen=True)
    write(ws, {"test_nested.py": NESTED_TEST})
    spec = {"requirements": [dict(NESTED_REQ, tests=["test_nested_rollback_only_inner"])]}
    result = judge(ws, task_spec=spec)
    req = _coverage(result)["requirements"][0]
    assert req["status"] == "VERIFIED", req
    assert result.decision == "PASS", result.insufficient_notes


def test_requirement_id_in_test_name_verifies(tmp_path):
    ws = corpus_workspace(tmp_path, TASK, "correct")
    write(ws, {"test_nested.py": NESTED_TEST.replace(
        "test_nested_rollback_only_inner", "test_req_001_nested_rollback")})
    result = judge(ws, task_spec={"requirements": [NESTED_REQ]})
    assert _coverage(result)["requirements"][0]["status"] == "VERIFIED"


def test_named_test_failing_on_buggy_code_is_conflicting_and_fails(tmp_path):
    ws = corpus_workspace(tmp_path, TASK, "wrong_rollback_all")
    write(ws, {"test_nested.py": NESTED_TEST})
    spec = {"requirements": [dict(NESTED_REQ, tests=["test_nested_rollback_only_inner"])]}
    result = judge(ws, task_spec=spec)
    assert _coverage(result)["requirements"][0]["status"] == "CONFLICTING"
    assert result.decision == "FAIL"


def test_keyword_overlap_with_unrelated_test_does_not_verify(tmp_path):
    # "rollback" appears in an existing single-level test name; keyword overlap with
    # the description is not evidence for the nested behaviour.
    ws = corpus_workspace(tmp_path, TASK, "wrong_rollback_all")
    spec = {"requirements": [{
        "id": "REQ-009",
        "description": "Nested rollback undoes only the innermost transaction",
        "priority": "critical",
    }]}
    result = judge(ws, task_spec=spec)
    assert _coverage(result)["requirements"][0]["status"] != "VERIFIED"
    assert result.decision != "PASS"

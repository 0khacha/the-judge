"""P1-6: probe triggers are keyword-based; the report must say so and must never
present behaviour that no probe or test exercised as verified.

Identical TTL-cache logic with renamed identifiers (limit/lifetime/store/fetch)
gets no expiration probe. The verdict for the buggy renamed cache must not be a
clean PASS that implies expiration was checked, and the report must list which
probes did not run and why.
"""

import contextlib
import io
import os

from audit_helpers import corpus_workspace, judge, repo_root

REPO = repo_root()


def _coverage(result):
    return result.trust_profile["probe_coverage"]


def test_renamed_buggy_cache_is_not_reported_as_expiration_verified(tmp_path):
    result = judge(corpus_workspace(tmp_path, "10_ttl_cache_renamed", "wrong_never_expires"))
    cov = _coverage(result)
    assert not any(p["kind"] == "expiration" for p in cov["ran"])
    not_run = {(p["symbol"], p["kind"]) for p in cov["not_run"]}
    assert ("ExpiringStore", "expiration") in not_run
    reasons = " ".join(p["reason"] for p in cov["not_run"])
    assert "keyword" in reasons
    beh = result.trust_profile["behavioral_coverage_subdimensions"]
    assert "VERIFIED" not in beh.values(), beh
    assert result.decision != "PASS"


def test_conventional_cache_reports_the_probes_that_ran(tmp_path):
    result = judge(corpus_workspace(tmp_path, "09_ttl_lru_cache", "correct"))
    ran = {(p["kind"], p["outcome"]) for p in _coverage(result)["ran"]}
    assert ("expiration", "passed") in ran and ("capacity_limit", "passed") in ran
    assert result.trust_profile["behavioral_coverage_subdimensions"]["state_coverage"] == "VERIFIED"


def test_no_canned_verified_subdimensions(tmp_path):
    # A plain function with a passing test: nothing adversarial or boundary-related
    # was checked, so the report must not claim it was.
    result = judge(corpus_workspace(tmp_path, "08_merge_intervals", "correct"))
    tp = result.trust_profile
    assert "VERIFIED" not in tp["behavioral_coverage_subdimensions"].values()
    assert "VERIFIED" not in tp["adversarial_robustness_subdimensions"].values()


def test_cli_report_says_probes_are_keyword_based_and_lists_unprobed(tmp_path):
    from the_judge.integrations.cli import main

    ws = corpus_workspace(tmp_path, "10_ttl_cache_renamed", "correct")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        main(["verify", ws])
    text = out.getvalue()
    assert "keyword" in text.lower()
    assert "ExpiringStore" in text


def test_readme_does_not_claim_vocabulary_free_probes():
    with open(os.path.join(REPO, "README.md"), encoding="utf-8") as f:
        readme = f.read().lower()
    assert "vocabulary-free" not in readme
    assert "keyword" in readme

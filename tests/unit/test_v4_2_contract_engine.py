import json
import os
import tempfile

from the_judge.core.contract_engine import ContractEngine
from the_judge.core.contract_parser import ContractParser
from the_judge.core.score_engine import evaluate
from the_judge.integrations.cli import main as cli_main


def test_contract_parser_basic():
    parser = ContractParser()
    spec_text = (
        "The HTTP client must retry 5xx responses up to 3 times. Fast responses are optimal."
    )
    res = parser.parse_natural_language_spec(spec_text)

    reqs = res["parsed_requirements"]
    assert len(reqs) >= 1
    assert any("retry" in r["description"].lower() for r in reqs)
    # Ambiguity detection for 'fast'
    assert len(res["ambiguities"]) >= 1


def test_contract_engine_evaluation():
    spec = {
        "task_id": "test_task",
        "requirements": [
            {
                "id": "REQ-001",
                "description": "Functional basic feature",
                "category": "functional",
                "priority": "critical",
                "properties": ["basic_feature"],
            },
            {
                "id": "REQ-002",
                "description": "Unverified security feature",
                "category": "security",
                "priority": "critical",
                "properties": ["unverified_secret_check"],
            },
        ],
    }
    engine = ContractEngine(task_spec=spec)

    ground_truth = {
        "test_suite": {
            "exit_code": 0,
            "passed_tests": ["test_req_req_001_basic_feature"],
            "failed_tests": [],
        },
        "test_provenance": {
            "test_req_req_001_basic_feature": {
                "source": "judge_challenge_test",
                "independence_level": "externally_verified",
                "confidence": "HIGH",
            }
        },
    }

    findings = {"requirements": [], "security_notes": []}

    res = engine.evaluate_contract_coverage(ground_truth, findings)
    summary = res["summary"]

    assert summary["total_requirements"] == 2
    assert summary["verified_count"] == 1
    assert summary["unverified_count"] == 1
    assert summary["critical_coverage_pct"] == 50.0
    assert "REQ-002" in summary["critical_unverified_ids"]


def test_hard_gate_9_coverage_gate():
    evidence = {
        "test_suite": {
            "exit_code": 0,
            "total_tests": 1,
            "passed_tests": ["test_prop_1"],
            "failed_tests": [],
        },
        "type_checker": {"exit_code": 0, "error_count": 0},
        "linter": {"exit_code": 0, "error_count": 0},
        "test_provenance": {
            "test_prop_1": {
                "source": "judge_challenge_test",
                "independence_level": "externally_verified",
            }
        },
        "challenge_manifest": {"file_tampered": False},
        "contract_data": {"summary": {"critical_unverified_ids": ["REQ-002"]}},
    }

    findings = {"requirements": [], "security_notes": []}
    res = evaluate(findings, evidence)

    # Hard Gate 9 must force ABSTAIN because REQ-002 is unverified
    assert res["verdict"] == "ABSTAIN"
    assert any("Coverage-Aware Gate" in note for note in res["insufficient_evidence_notes"])


def test_judge_contract_cli():
    with tempfile.TemporaryDirectory() as tmp_dir:
        spec_file = os.path.join(tmp_dir, "task_spec.json")
        with open(spec_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "task_id": "cli_test",
                    "requirements": [
                        {"id": "REQ-001", "description": "CLI spec test", "priority": "critical"}
                    ],
                },
                f,
            )

        ret = cli_main(["contract", tmp_dir, "--json"])
        assert ret == 0

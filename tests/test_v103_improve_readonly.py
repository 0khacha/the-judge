"""`judge improve` is read-only unless the user opts in with --apply / apply=True.

Previously the built-in AutoImprover edited user files by default and wrote
placeholder tests (`assert callable(f)`, `assert True`, `pytest.raises` around a
bare `raise`), which the judge then counted as independent evidence.
"""

import hashlib
import os

from the_judge.api import improve
from the_judge.integrations.auto_improver import AutoImprover
from the_judge.integrations.cli import main

SILENT = "def div(a, b):\n    try:\n        return a / b\n    except Exception:\n        pass\n"


def _snapshot(root):
    """Hash every file outside the judge's own report directories."""
    out = {}
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(("_judge", ".judge", "__pycache__"))]
        for name in files:
            path = os.path.join(dirpath, name)
            with open(path, "rb") as f:
                out[os.path.relpath(path, root)] = hashlib.sha256(f.read()).hexdigest()
    return out


def _test_files(root):
    return sorted(p for p in _snapshot(root) if os.path.basename(p).startswith("test_"))


def test_api_improve_default_does_not_modify_workspace(tmp_path):
    (tmp_path / "calc.py").write_text(SILENT)
    before = _snapshot(tmp_path)
    result = improve(workspace=str(tmp_path), max_rounds=3)
    assert _snapshot(tmp_path) == before
    assert result["outcome"] == "REVIEW_ONLY"
    assert result["total_rounds"] == 1
    assert isinstance(result["suggestions"], list)
    assert "apply" in result["reason"]


def test_cli_improve_default_does_not_modify_workspace(tmp_path, capsys):
    (tmp_path / "calc.py").write_text(SILENT)
    before = _snapshot(tmp_path)
    code = main(["improve", str(tmp_path), "--no-report"])
    assert _snapshot(tmp_path) == before
    out = capsys.readouterr().out
    assert "REVIEW_ONLY" in out
    assert "--apply" in out
    assert code == 1


def test_cli_improve_apply_edits_workspace(tmp_path):
    (tmp_path / "calc.py").write_text(SILENT)
    main(["improve", str(tmp_path), "--apply", "--max-rounds", "2", "--no-report"])
    assert (tmp_path / "calc.py").read_text() != SILENT


def test_auto_improver_never_writes_tests_without_tests(tmp_path):
    (tmp_path / "calc.py").write_text(SILENT)
    AutoImprover(str(tmp_path)).improve_workspace({"decision": "ABSTAIN", "critique": {}})
    assert _test_files(tmp_path) == []


def test_auto_improver_never_writes_tests_for_findings(tmp_path):
    (tmp_path / "calc.py").write_text(SILENT)
    findings = [
        {"id": "C1", "evidence_level": "contradicted", "description": "claim is false",
         "agent_claim": "all edge cases handled"},
        {"id": "C2", "evidence_level": "observed", "description": "No test covers None input"},
    ]
    AutoImprover(str(tmp_path)).improve_workspace(
        {"decision": "FAIL", "critique": {"improvement_priority": findings}})
    assert _test_files(tmp_path) == []

import os
import shutil
import tempfile
import pytest
from the_judge.api import improve
from the_judge.integrations.auto_improver import AutoImprover


def test_auto_improver_basic():
    temp_dir = tempfile.mkdtemp()
    try:
        # Create a sample python file without tests
        sample_py = os.path.join(temp_dir, "sample.py")
        with open(sample_py, "w", encoding="utf-8") as f:
            f.write("def add(a, b):\n    return a + b\n")

        improver = AutoImprover(temp_dir)
        res = improver.improve_workspace({"decision": "ABSTAIN", "findings": []})

        assert res["improved"] is True
        assert any("test" in change.lower() for change in res["changes"])
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_improve_api_loop():
    temp_dir = tempfile.mkdtemp()
    try:
        sample_py = os.path.join(temp_dir, "math_utils.py")
        with open(sample_py, "w", encoding="utf-8") as f:
            f.write("def multiply(x, y):\n    return x * y\n")

        result = improve(workspace=temp_dir, max_rounds=3, target_score=80.0)

        assert "outcome" in result
        assert "history" in result
        assert len(result["history"]) >= 1
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

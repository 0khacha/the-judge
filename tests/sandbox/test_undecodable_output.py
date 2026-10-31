"""Test output that is not valid in the locale encoding does not break verification.

The sandbox decoded pytest's stdout with the locale code page and no error handler; a
test printing bytes that code page cannot decode (0x81 under cp1252, or any invalid
UTF-8) made the reader thread raise and the captured output was lost.
"""

from the_judge.core.sandbox import SandboxRunner


def test_run_cmd_survives_undecodable_bytes(tmp_path):
    import sys

    res = SandboxRunner.run_cmd(
        [sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'ok \\x81\\xff end\\n')"],
        cwd=str(tmp_path),
    )
    assert res["exit_code"] == 0
    assert res["stdout"].startswith("ok ") and res["stdout"].rstrip().endswith("end")


def test_baseline_reads_committed_utf8_tests_exactly(tmp_path):
    import subprocess

    from the_judge.core.baseline import compare_tests_to_baseline

    (tmp_path / "test_msg.py").write_text(
        "def test_msg():\n    assert 'añadir → 加法' == 'añadir → 加法', 'résumé ✓'\n",
        encoding="utf-8",
    )
    for args in (["init", "-q"], ["add", "-A"],
                 ["-c", "user.email=a@b", "-c", "user.name=t", "commit", "-qm", "init"]):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True,
                       stdin=subprocess.DEVNULL)
    result = compare_tests_to_baseline(str(tmp_path))
    assert result["issues"] == []
    assert result["unchanged_tests"] == ["test_msg"]

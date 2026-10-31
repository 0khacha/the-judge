"""The git-baseline tamper check only looks at files pytest would collect.

Previously every tracked test_*.py was compared, so test files outside `testpaths` or
under `norecursedirs` (fixtures, benchmark corpora) were reported as "removed" -- a
blocking TAMPERING finding on an untouched repository.
"""

import subprocess

from the_judge.core.baseline import compare_tests_to_baseline

TEST = "def test_{name}():\n    assert 1 + 1 == 2\n"


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                   stdin=subprocess.DEVNULL)


def _repo(tmp_path, pyproject):
    (tmp_path / "pyproject.toml").write_text(pyproject)
    for rel in ("tests/test_core.py", "fixtures/test_fixture.py",
                "tests/corpus/test_sample.py"):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(TEST.format(name=path.stem))
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "-c", "user.email=a@b", "-c", "user.name=t", "commit", "-qm", "init")


def test_files_outside_testpaths_are_not_reported_removed(tmp_path):
    _repo(tmp_path, '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n')
    result = compare_tests_to_baseline(str(tmp_path))
    assert result["checked"]
    assert [i for i in result["issues"] if "fixture" in i["file"]] == []


def test_files_under_norecursedirs_are_not_reported_removed(tmp_path):
    _repo(tmp_path, '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n'
                    'norecursedirs = ["corpus"]\n')
    assert compare_tests_to_baseline(str(tmp_path))["issues"] == []


def test_removed_test_inside_testpaths_is_still_reported(tmp_path):
    _repo(tmp_path, '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n')
    (tmp_path / "tests" / "test_core.py").write_text("x = 1\n")
    issues = compare_tests_to_baseline(str(tmp_path))["issues"]
    assert [(i["kind"], i["test"]) for i in issues] == [("deleted_test", "test_test_core")]


def test_deleted_test_file_inside_testpaths_is_still_reported(tmp_path):
    _repo(tmp_path, '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n')
    (tmp_path / "tests" / "test_core.py").unlink()
    kinds = {i["kind"] for i in compare_tests_to_baseline(str(tmp_path))["issues"]}
    assert "deleted_test_file" in kinds

"""The version is defined once (the_judge.__version__) and reported everywhere from it."""

import contextlib
import os
import re

from the_judge import __version__
from the_judge.core.decision import VerificationResult
from the_judge.integrations.cli import main

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_pyproject_matches_package_version():
    with open(os.path.join(ROOT, "pyproject.toml"), encoding="utf-8") as f:
        assert f'version = "{__version__}"' in f.read()


def test_cli_version_flag(capsys):
    with contextlib.suppress(SystemExit):
        main(["--version"])
    assert __version__ in capsys.readouterr().out


def test_result_reports_package_version():
    r = VerificationResult("PASS", 100.0, {}, [], {}, [], [])
    assert r.to_dict()["runtime"]["judge_version"] == f"v{__version__}"


def test_no_hard_coded_version_literals_in_package():
    pattern = re.compile(r"\d+\.\d+\.\d+")
    offenders = []
    for dirpath, _, files in os.walk(os.path.join(ROOT, "the_judge")):
        for name in files:
            if not name.endswith(".py") or name == "_version.py":
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding="utf-8") as f:
                for n, line in enumerate(f, 1):
                    if __version__ in line and pattern.search(line):
                        offenders.append(f"{os.path.relpath(path, ROOT)}:{n}")
    assert offenders == []


def test_no_literal_judge_version_fields():
    offenders = []
    for dirpath, _, files in os.walk(os.path.join(ROOT, "the_judge")):
        for name in files:
            if name.endswith(".py"):
                path = os.path.join(dirpath, name)
                with open(path, encoding="utf-8") as f:
                    for n, line in enumerate(f, 1):
                        if re.search(r"""["']judge_version["']\s*:\s*["']""", line):
                            offenders.append(f"{os.path.relpath(path, ROOT)}:{n}")
    assert offenders == []

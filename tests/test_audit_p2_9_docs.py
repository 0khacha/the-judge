"""P2-9: packaging and documentation honesty.

* `pip install the-judge` from PyPI installs an UNRELATED package, so no doc may
  tell users to install from PyPI by that name; install from git instead.
* Benchmark reports produced with the scripted TestAgent must say they are
  simulated, not "real".
* No tracked file may point at audit documents that are not in the repository.
* README documents optional tooling and current known limitations.
"""

import os
import re
import subprocess

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GIT_INSTALL = "git+https://github.com/0khacha/the-judge.git"
PYPI_INSTALL = re.compile(r"pip install\s+[\"']?the[-_]judge(\[[^\]]*\])?[\"']?(?![\w.+/-])")


def _tracked(*suffixes):
    out = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True,
                         stdin=subprocess.DEVNULL, check=True).stdout.split()
    return [p for p in out if p.endswith(suffixes) and not p.startswith("tests/")]


def _read(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8", errors="replace") as f:
        return f.read()


def test_no_doc_installs_the_unrelated_pypi_package():
    offenders = []
    for rel in _tracked(".md", ".txt", ".sh", ".bat", ".yml", ".yaml", ".toml"):
        for n, line in enumerate(_read(rel).splitlines(), 1):
            if PYPI_INSTALL.search(line):
                offenders.append(f"{rel}:{n}: {line.strip()}")
    assert offenders == []


@pytest.mark.parametrize("rel", ["README.md", "INSTALL.md", "AGENTS.md", "docs/QUICK_START.md"])
def test_install_docs_use_git(rel):
    assert GIT_INSTALL in _read(rel)


def test_readme_copy_paste_prompt_installs_the_renamed_distribution():
    # The README is frozen into the PyPI project page at upload, so it already
    # names the published distribution; git stays as the "latest from main" option.
    readme = _read("README.md")
    prompt = readme[readme.index("Copy/paste into your AI assistant"):]
    prompt = prompt[:prompt.index("```", prompt.index("```") + 3)]
    assert "pip install the-judge-verify" in prompt
    assert GIT_INSTALL in readme
    assert "not yet on PyPI" not in readme
    assert "pypi.org/project/the-judge/" not in readme  # badges pointed at the other package


def test_readme_has_no_relative_links_or_images():
    # README.md is the PyPI long description; relative paths break there.
    readme = _read("README.md")
    refs = re.findall(r'\]\(([^)]+)\)|(?:src|href)="([^"]+)"', readme)
    relative = [a or b for a, b in refs
                if not re.match(r"(https?://|mailto:|#)", a or b)]
    assert relative == []
    assert "https://raw.githubusercontent.com/0khacha/the-judge/main/logo.svg" in readme


@pytest.mark.parametrize("rel", [
    "benchmark/results/agent/report/agent_benchmark_report.md",
    "benchmark/THE_JUDGE_AGENT_BENCHMARK_REPORT.md",
])
def test_simulated_agent_benchmark_is_labelled_simulated(rel):
    text = _read(rel)
    assert "SIMULATED" in text
    for claim in ("Real Coding-Agent", "Real Token Overhead", "(Real Tokens)", "Real Agents"):
        assert claim not in text, claim


def test_report_generator_labels_non_real_runs_as_simulated():
    import sys

    sys.path.insert(0, REPO)
    from benchmark.agent.agent_report_generator import generate_agent_report

    text = generate_agent_report({}, [], {}, {"mode": "test"})
    first = text.splitlines()[0]
    assert "SIMULATED" in first and "Real" not in first


def test_no_dangling_references_to_missing_audit_documents():
    missing = [name for name in ("LEVEL2_AUDIT_REPORT.md", "JUDGE_CORE_DEFECTS.md")
               if not any(p.endswith(name) for p in _tracked(".md"))]
    offenders = []
    for rel in _tracked(".md", ".py", ".txt"):
        text = _read(rel)
        offenders += [f"{rel}: {name}" for name in missing if name in text]
    assert offenders == []


def test_readme_documents_optional_tools_and_limitations():
    readme = _read("README.md")
    assert "known limitations" in readme.lower()
    assert "mypy" in readme and "ruff" in readme and "optional" in readme.lower()
    for rel in ("INSTALL.md", "docs/QUICK_START.md"):
        text = _read(rel)
        assert "optional" in text.lower() and "mypy" in text, rel


def test_distribution_name_does_not_collide_with_the_pypi_project():
    # 'the-judge' on PyPI belongs to another author. The distribution is published as
    # 'the-judge-verify'; the import package stays `the_judge` and the CLI `judge`.
    pyproject = _read("pyproject.toml")
    assert re.search(r'^name = "the-judge-verify"$', pyproject, re.M)
    readme = _read("README.md")
    assert "the-judge-verify" in readme and "import the_judge" in readme
    assert "pip uninstall the-judge-verify" in _read("INSTALL.md")

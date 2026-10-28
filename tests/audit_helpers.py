"""Helpers for the audit regression tests: build workspaces from tests/regression_audit."""

import os
import shutil
import subprocess

CORPUS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "regression_audit", "tasks")


def corpus_workspace(dest, task, variant="correct", tests_subdir=None, git_baseline=False):
    """Copy a corpus variant plus its visible tests into dest and return the path.

    tests_subdir: put the visible tests in this sub-directory instead of the root.
    git_baseline: commit the variant's baseline/ files at HEAD first, then write the
                  variant's own files on top (simulates tests edited after commit).
    """
    dest = str(dest)
    os.makedirs(dest, exist_ok=True)
    task_dir = os.path.join(CORPUS, task)
    variant_dir = os.path.join(task_dir, "variants", variant)
    test_dir = os.path.join(dest, tests_subdir) if tests_subdir else dest
    os.makedirs(test_dir, exist_ok=True)

    visible = {}
    vis_dir = os.path.join(task_dir, "visible")
    for name in os.listdir(vis_dir):
        visible[name] = os.path.join(vis_dir, name)
    for name in os.listdir(variant_dir):
        path = os.path.join(variant_dir, name)
        if not os.path.isfile(path):
            continue
        if name.startswith("test_"):
            visible[name] = path
        else:
            shutil.copy2(path, os.path.join(dest, name))

    baseline_dir = os.path.join(variant_dir, "baseline")
    if git_baseline:
        for name, path in visible.items():
            base = os.path.join(baseline_dir, name)
            shutil.copy2(base if os.path.exists(base) else path, os.path.join(test_dir, name))
        git(dest, "init", "-q")
        git(dest, "add", "-A")
        git(dest, "commit", "-q", "-m", "baseline")
    for name, path in visible.items():
        shutil.copy2(path, os.path.join(test_dir, name))
    return dest


def git(cwd, *args):
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
        cwd=cwd, check=True, capture_output=True, stdin=subprocess.DEVNULL,
    )


def write(dest, files):
    """Write {relative_path: source} into dest and return dest as str."""
    dest = str(dest)
    for rel, text in files.items():
        path = os.path.join(dest, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    return dest


def judge(workspace, task_spec=None):
    from the_judge.api import verify

    return verify(str(workspace), task_spec=task_spec)


def judge_authored_failures(result):
    """Failed tests that the judge itself generated (probes / property challenges)."""
    return [
        f.description for f in result.findings
        if f.category == "behavior" and ("_prop_" in f.description or "test_behavior_" in f.description)
    ]

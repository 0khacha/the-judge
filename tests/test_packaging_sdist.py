"""The source distribution must contain only files tracked by git.

MANIFEST.in's recursive-include patterns pick up whatever is on disk, so local,
git-ignored files (benchmark scratch results, private reports) would otherwise be
published to PyPI with the sdist.
"""

import os
import subprocess
import sys
import tarfile

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERATED = ("PKG-INFO", "setup.cfg", "the_judge_verify.egg-info/")


def test_sdist_contains_only_tracked_files(tmp_path):
    pytest.importorskip("build")
    proc = subprocess.run(
        [sys.executable, "-m", "build", "--sdist", "--no-isolation", "--outdir", str(tmp_path), REPO],
        capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=600,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    (sdist,) = list(tmp_path.glob("*.tar.gz"))
    tracked = set(subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True,
                                 stdin=subprocess.DEVNULL, check=True).stdout.split())
    with tarfile.open(sdist) as tar:
        files = [m.name.split("/", 1)[1] for m in tar.getmembers() if m.isfile() and "/" in m.name]
    untracked = [f for f in files if f not in tracked and not f.startswith(GENERATED)]
    assert untracked == []

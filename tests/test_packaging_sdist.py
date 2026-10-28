"""Published distributions must contain the package and only files tracked by git.

MANIFEST.in's recursive-include patterns pick up whatever is on disk, so local,
git-ignored files (benchmark scratch results, private reports) would otherwise be
published to PyPI with the sdist. Conversely, an over-broad exclude can silently
drop the package itself; `python -m build` builds the wheel from the sdist, so the
wheel would then be empty.
"""

import os
import subprocess
import sys
import tarfile
import zipfile

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERATED = ("PKG-INFO", "setup.cfg", "the_judge_verify.egg-info/")
REQUIRED = ("the_judge/__init__.py", "the_judge/api.py", "the_judge/core/sandbox.py",
            "the_judge/integrations/cli.py", "judge/__init__.py")


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    pytest.importorskip("build")
    out = tmp_path_factory.mktemp("dist")
    proc = subprocess.run(
        [sys.executable, "-m", "build", "--no-isolation", "--outdir", str(out), REPO],
        capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=900,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    (sdist,) = list(out.glob("*.tar.gz"))
    (wheel,) = list(out.glob("*.whl"))
    with tarfile.open(sdist) as tar:
        sdist_files = [m.name.split("/", 1)[1] for m in tar.getmembers() if m.isfile() and "/" in m.name]
    with zipfile.ZipFile(wheel) as whl:
        wheel_files = whl.namelist()
    return sdist_files, wheel_files


def test_sdist_contains_only_tracked_files(built):
    sdist_files, _ = built
    tracked = set(subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True,
                                 stdin=subprocess.DEVNULL, check=True).stdout.split())
    untracked = [f for f in sdist_files if f not in tracked and not f.startswith(GENERATED)]
    assert untracked == []


@pytest.mark.parametrize("which", ["sdist", "wheel"])
def test_distributions_contain_the_package(built, which):
    files = set(built[0] if which == "sdist" else built[1])
    missing = [f for f in REQUIRED if f not in files]
    assert missing == []

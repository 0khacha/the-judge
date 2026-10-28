"""P2-8: code must not be able to tell the sandbox apart by a fixed path prefix.

The sandbox used to run from tempfile.mkdtemp(prefix="t_<uuid>_"), so an
implementation could return correct answers only when basename(cwd) started with
"t_". It now runs from a neutral cwd (the workspace, as a developer would) and the
sandbox directories have randomized names with no fixed prefix. This is not a
security boundary against a hostile implementation (see README / SECURITY.md).
"""

import json
import os
import subprocess
import sys

from audit_helpers import judge, write
from the_judge.core.sandbox import SandboxRunner

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CHEATER = '''
import os


def add(a, b):
    # Correct only when it believes it is being judged.
    if os.path.basename(os.getcwd()).startswith("t_"):
        return a + b
    return a - b
'''
CHEATER_TEST = "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"


def test_cwd_prefix_check_behaves_the_same_inside_and_outside(tmp_path):
    ws = write(tmp_path / "ws", {"calc.py": CHEATER, "test_calc.py": CHEATER_TEST})
    outside = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", ws],
        cwd=ws, capture_output=True, text=True, stdin=subprocess.DEVNULL,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
    )
    assert outside.returncode != 0  # the bug shows outside the sandbox
    result = judge(ws)
    assert result.decision == "FAIL", result.to_dict()  # ...and inside it


SPY = '''
import json
import os


def test_where_am_i():
    print("SPY" + json.dumps({"cwd": os.getcwd(), "file_dir": os.path.dirname(os.path.abspath(__file__))}))
'''


def _spy(ws):
    res = SandboxRunner.execute_in_anonymous_sandbox(
        ws, [("suite_marker/test_spy.py", SPY)], pytest_args=["-s"]
    )
    line = next(ln for ln in res["stdout"].splitlines() if "SPY{" in ln)
    return json.loads(line[line.index("SPY") + 3:])


def test_sandbox_paths_have_no_fixed_prefix_and_are_randomized(tmp_path):
    ws = write(tmp_path / "ws", {"calc.py": "X = 1\n"})
    first, second = _spy(ws), _spy(ws)
    for seen in (first, second):
        assert not os.path.basename(seen["cwd"]).startswith("t_")
        assert os.path.realpath(seen["cwd"]) == os.path.realpath(ws)
    # The sandbox root holding the tests changes from run to run.
    root1 = os.path.dirname(first["file_dir"])
    root2 = os.path.dirname(second["file_dir"])
    assert os.path.basename(root1) != os.path.basename(root2)
    assert not os.path.basename(root1).startswith("t_")


def test_workspace_suite_dir_name_is_not_fixed(tmp_path):
    ws = write(tmp_path / "ws", {
        "calc.py": "def add(a, b):\n    return a + b\n",
        "tests/test_calc.py": (
            "import os\nfrom calc import add\n\n"
            "def test_add():\n"
            "    parts = os.path.abspath(__file__).split(os.sep)\n"
            "    assert 'suite' not in parts\n"
            "    assert add(1, 2) == 3\n"
        ),
    })
    assert judge(ws).provenance["failed_tests"] == 0


def test_docs_state_sandbox_is_not_a_security_boundary():
    for name in ("README.md", "SECURITY.md"):
        with open(os.path.join(REPO, name), encoding="utf-8") as f:
            assert "not a security boundary" in f.read().lower(), name


def test_cli_json_still_parses_with_relative_test_paths(tmp_path):
    ws = write(tmp_path / "ws", {
        "data/expected.json": "[1, 2]",
        "calc.py": "def pair():\n    return [1, 2]\n",
        "test_calc.py": (
            "import json\nfrom calc import pair\n\n"
            "def test_pair_matches_fixture_file():\n"
            "    with open('data/expected.json') as f:\n"
            "        assert pair() == json.load(f)\n"
        ),
    })
    launcher = (
        "import sys; sys.path.insert(0, sys.argv.pop(1)); "
        "from the_judge.integrations.cli import main; sys.exit(main(sys.argv[1:]))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", launcher, REPO, "verify", ws, "--json"],
        capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=600,
    )
    data = json.loads(proc.stdout[proc.stdout.index("{"):])
    assert data["provenance"]["failed_tests"] == 0, data["blocking_issues"]

"""CLI output survives non-ASCII text when stdout is a pipe on a legacy code page.

On Windows a piped stdout defaults to the ANSI code page (cp1252), which cannot
encode e.g. "→" or CJK text. Test failure messages from the user's code end up in
the report, so printing them used to crash `judge verify` with UnicodeEncodeError.
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_verify_report_with_non_cp1252_text_on_cp1252_pipe(tmp_path):
    (tmp_path / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (tmp_path / "test_calc.py").write_text(
        "from calc import add\n\n\ndef test_add():\n"
        "    assert add(1, 2) == 3, 'add(1, 2) → 3 ✓ 加法'\n",
        encoding="utf-8",
    )
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}
    env.update(PYTHONPATH=ROOT, PYTHONIOENCODING="cp1252")
    result = subprocess.run(
        [sys.executable, "-c", "import sys; from the_judge.integrations.cli import main; "
         "sys.exit(main(['verify', sys.argv[1], '--no-mutation']))", str(tmp_path)],
        capture_output=True, stdin=subprocess.DEVNULL, timeout=300, env=env, cwd=str(tmp_path),
    )
    err = result.stderr.decode("utf-8", "replace")
    assert "UnicodeEncodeError" not in err, err[-2000:]
    assert result.returncode == 1, err[-2000:]
    assert "test_add" in result.stdout.decode("utf-8", "replace")

"""Workspace test discovery for The Judge.

Finds the workspace's own tests the way pytest would without arguments: it honours
``testpaths``, ``python_files`` and ``norecursedirs`` from pytest.ini, pyproject.toml
([tool.pytest.ini_options]), tox.ini or setup.cfg, and never descends into virtual
environments, node_modules, build output, caches, hidden directories or .git.
"""

import ast
import configparser
import fnmatch
import glob
import os
import re
from typing import Any, Optional

DEFAULT_PYTHON_FILES = ["test_*.py", "*_test.py"]

# Directory names never searched for tests (in addition to any hidden directory
# and any directory that is itself a virtualenv, i.e. contains pyvenv.cfg).
EXCLUDED_DIRS = frozenset({
    "__pycache__", "node_modules", "venv", "env", "site-packages",
    "build", "dist", "_judge_visual", "_darcs", "CVS", "{arch}",
})


def _split_ini_list(value: str) -> list[str]:
    return [v for v in re.split(r"[\s,]+", value.strip()) if v]


def _toml_pytest_section(text: str) -> dict[str, Any]:
    try:
        import tomllib  # Python 3.11+

        return dict(tomllib.loads(text).get("tool", {}).get("pytest", {}).get("ini_options", {}))
    except ImportError:
        pass
    except Exception:
        return {}
    # Minimal fallback for Python < 3.11: string and string-array values only.
    match = re.search(r"^\[tool\.pytest\.ini_options\]\s*$(.*?)(?=^\[|\Z)", text, re.M | re.S)
    if not match:
        return {}
    options: dict[str, Any] = {}
    for key, raw in re.findall(r"^(\w+)\s*=\s*(\[.*?\]|\"[^\"]*\"|'[^']*')", match.group(1), re.M | re.S):
        try:
            options[key] = ast.literal_eval(raw)
        except (ValueError, SyntaxError):
            continue
    return options


def read_pytest_config(abs_dir: str) -> dict[str, Any]:
    """Return {"testpaths": [...], "python_files": [...], "norecursedirs": [...]}.

    Follows pytest's precedence: pytest.ini, pyproject.toml, tox.ini, setup.cfg.
    """
    options: Optional[dict[str, Any]] = None
    ini_path = os.path.join(abs_dir, "pytest.ini")
    toml_path = os.path.join(abs_dir, "pyproject.toml")
    if os.path.isfile(ini_path):
        options = _ini_section(ini_path, "pytest") or {}
    elif os.path.isfile(toml_path):
        with open(toml_path, encoding="utf-8") as f:
            options = _toml_pytest_section(f.read()) or None
    if options is None:
        for name, section in (("tox.ini", "pytest"), ("setup.cfg", "tool:pytest")):
            path = os.path.join(abs_dir, name)
            if os.path.isfile(path):
                found = _ini_section(path, section)
                if found is not None:
                    options = found
                    break
    options = options or {}

    def as_list(value: Any) -> list[str]:
        if value is None:
            return []
        return _split_ini_list(value) if isinstance(value, str) else [str(v) for v in value]

    return {
        "testpaths": as_list(options.get("testpaths")),
        "python_files": as_list(options.get("python_files")) or list(DEFAULT_PYTHON_FILES),
        "norecursedirs": as_list(options.get("norecursedirs")),
    }


def _ini_section(path: str, section: str) -> Optional[dict[str, Any]]:
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read(path, encoding="utf-8")
    except configparser.Error:
        return None
    if not parser.has_section(section):
        return None
    return dict(parser.items(section))


def _is_excluded_dir(path: str, name: str, extra_patterns: list[str]) -> bool:
    if name.startswith(".") or name in EXCLUDED_DIRS or name.endswith(".egg-info"):
        return True
    if any(fnmatch.fnmatch(name, pat) for pat in extra_patterns):
        return True
    return os.path.isfile(os.path.join(path, "pyvenv.cfg"))


def _test_roots(abs_dir: str, config: dict[str, Any]) -> list[str]:
    roots: list[str] = []
    for entry in config["testpaths"] or ["."]:
        for match in sorted(glob.glob(os.path.join(abs_dir, entry))):
            if os.path.abspath(match).startswith(abs_dir):
                roots.append(os.path.abspath(match))
    return roots


def collects(abs_dir: str, relpath: str) -> bool:
    """True if discovery would collect ``relpath`` (relative to abs_dir) were it on disk.

    Applies the same testpaths / norecursedirs / python_files rules as
    discover_workspace_tests, so it also answers for files that no longer exist.
    """
    abs_dir = os.path.abspath(abs_dir)
    config = read_pytest_config(abs_dir)
    path = os.path.abspath(os.path.join(abs_dir, relpath))
    if not (path.endswith(".py")
            and any(fnmatch.fnmatch(os.path.basename(path), p) for p in config["python_files"])):
        return False
    for root in _test_roots(abs_dir, config):
        if path == root:
            return True
        rel = os.path.relpath(os.path.dirname(path), root)
        if rel == ".":
            return True
        if rel.startswith(".."):
            continue
        current = root
        for part in rel.split(os.sep):
            current = os.path.join(current, part)
            if _is_excluded_dir(current, part, config["norecursedirs"]):
                break
        else:
            return True
    return False


def discover_workspace_tests(abs_dir: str) -> list[str]:
    """Return workspace test files as sorted paths relative to abs_dir."""
    config = read_pytest_config(abs_dir)
    patterns = config["python_files"]
    norecurse = config["norecursedirs"]
    roots = _test_roots(abs_dir, config)

    found: set[str] = set()
    for root in roots:
        if os.path.isfile(root):
            found.add(os.path.relpath(root, abs_dir))
            continue
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = sorted(
                d for d in dirs if not _is_excluded_dir(os.path.join(dirpath, d), d, norecurse)
            )
            for fname in files:
                if fname.endswith(".py") and any(fnmatch.fnmatch(fname, p) for p in patterns):
                    found.add(os.path.relpath(os.path.join(dirpath, fname), abs_dir))
    return sorted(found)


def support_files(abs_dir: str, test_relpaths: list[str]) -> list[str]:
    """Files the discovered tests need besides themselves, relative to abs_dir.

    * every conftest.py from the workspace root down to each test's directory;
    * for tests outside the root: the other .py files of their directory and the
      __init__.py chain, so sibling imports (``from helpers import x``) and package
      imports keep working when the tests are copied into the sandbox.
    """
    test_set = set(test_relpaths)
    needed: set[str] = set()
    for rel in test_relpaths:
        parts = os.path.dirname(rel).split(os.sep) if os.path.dirname(rel) else []
        for depth in range(len(parts) + 1):
            sub = os.path.join(*parts[:depth]) if depth else ""
            conftest = os.path.join(sub, "conftest.py")
            if os.path.isfile(os.path.join(abs_dir, conftest)):
                needed.add(os.path.normpath(conftest))
            if depth:
                init = os.path.join(sub, "__init__.py")
                if os.path.isfile(os.path.join(abs_dir, init)):
                    needed.add(os.path.normpath(init))
        if parts:
            test_dir = os.path.join(abs_dir, *parts)
            for fname in os.listdir(test_dir):
                rel_f = os.path.normpath(os.path.join(*parts, fname))
                if fname.endswith(".py") and rel_f not in test_set:
                    needed.add(rel_f)
    return sorted(needed - test_set)


# Limits for data files copied next to the tests (fixtures, corpora).
MAX_DATA_FILE_BYTES = 5 * 1024 * 1024
MAX_DATA_TOTAL_BYTES = 50 * 1024 * 1024


def data_files(abs_dir: str, test_relpaths: list[str]) -> list[str]:
    """Files besides the tests that the sandbox copies, relative to abs_dir.

    Tests often find data relative to themselves (``Path(__file__).parent / "data"``,
    ``Path(__file__).parents[1] / "README.md"``), so the sandbox mirrors the layout:

    * everything under the directories that hold the tests (fixtures, corpora),
      except test-pattern files and conftest.py files discovery did not select --
      unless they lie under a ``norecursedirs`` directory, which the sandbox's
      pytest also skips, so they are readable there but never run;
    * the non-Python, non-hidden files of the rest of the workspace (no
      implementation module, ``.env`` or similar is duplicated into the sandbox).

    Byte code, excluded directories (hidden, venvs, node_modules, ...), files over
    MAX_DATA_FILE_BYTES and anything beyond MAX_DATA_TOTAL_BYTES are skipped; test
    directories are walked first, so the files next to the tests are kept.
    """
    abs_dir = os.path.abspath(abs_dir)
    config = read_pytest_config(abs_dir)
    patterns, norecurse = config["python_files"], config["norecursedirs"]
    taken = {os.path.normpath(p) for p in test_relpaths}
    taken.update(os.path.normpath(p) for p in support_files(abs_dir, test_relpaths))
    dirs = sorted({os.path.dirname(os.path.normpath(p)) for p in test_relpaths} - {""})
    roots = [(d, True) for d in dirs if not any(d.startswith(o + os.sep) for o in dirs)]
    roots.append(("", False))

    out: list[str] = []
    seen: set[str] = set()
    total = 0
    for root, test_dir in roots:
        inert_dirs: set[str] = set()  # under norecursedirs: never collected
        for dirpath, dirnames, files in os.walk(os.path.join(abs_dir, root)):
            dirnames[:] = sorted(
                d for d in dirnames if not _is_excluded_dir(os.path.join(dirpath, d), d, [])
            )
            inert = dirpath in inert_dirs
            for d in dirnames:
                if inert or any(fnmatch.fnmatch(d, pat) for pat in norecurse):
                    inert_dirs.add(os.path.join(dirpath, d))
            for fname in sorted(files):
                rel = os.path.relpath(os.path.join(dirpath, fname), abs_dir)
                if rel in taken or rel in seen or fname.endswith((".pyc", ".pyo")):
                    continue
                is_python = fname.endswith((".py", ".pyd"))
                runnable = fname == "conftest.py" or (
                    fname.endswith(".py") and any(fnmatch.fnmatch(fname, p) for p in patterns))
                # Outside the test directories, hidden files are config or secrets (.env).
                hidden = fname.startswith(".") and not test_dir
                if (is_python and not test_dir) or (runnable and not inert) or hidden:
                    continue
                try:
                    size = os.path.getsize(os.path.join(abs_dir, rel))
                except OSError:
                    continue
                if size > MAX_DATA_FILE_BYTES or total + size > MAX_DATA_TOTAL_BYTES:
                    continue
                total += size
                seen.add(rel)
                out.append(rel)
    return out


def import_roots(abs_dir: str) -> list[str]:
    """Directories to put on PYTHONPATH so workspace code is importable (root, src/)."""
    roots = [abs_dir]
    src = os.path.join(abs_dir, "src")
    if os.path.isdir(src):
        roots.append(src)
    return roots


def workspace_module_names(abs_dir: str) -> set[str]:
    """Importable top-level names defined by the workspace (modules and packages)."""
    names: set[str] = set()
    for root in import_roots(abs_dir):
        for fname in os.listdir(root):
            path = os.path.join(root, fname)
            if fname.endswith(".py") and not fname.startswith(("test_", "_")):
                names.add(fname[:-3])
            elif os.path.isfile(os.path.join(path, "__init__.py")) and not fname.startswith((".", "_")):
                names.add(fname)
    return names

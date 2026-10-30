"""Files next to the tests (fixtures, corpora) are available in the sandbox.

Tests that locate data through ``__file__`` (``Path(__file__).parent / "data"``)
used to fail to import in the sandbox, and the verdict was FAIL with
"COLLECTION TAMPERING DETECTED" for a correct, untouched project.
"""

import os

from the_judge.api import verify

PARSER = "def parse(s):\n    return s.strip().split(',')\n"


def _project(tmp_path, test_body, pyproject=None):
    (tmp_path / "parser.py").write_text(PARSER)
    (tmp_path / "tests" / "data").mkdir(parents=True)
    (tmp_path / "tests" / "data" / "sample.csv").write_text("a,b\n")
    (tmp_path / "tests" / "data" / "blob.bin").write_bytes(bytes(range(256)))
    (tmp_path / "tests" / "test_parser.py").write_text(
        "import os\nfrom parser import parse\n\n"
        "HERE = os.path.dirname(os.path.abspath(__file__))\n\n" + test_body
    )
    if pyproject:
        (tmp_path / "pyproject.toml").write_text(pyproject)


def _run(tmp_path):
    result = verify(str(tmp_path), record_history=False, mutation=False)
    suite = result.trust_profile
    return result, suite


def test_text_fixture_read_at_import_via_file(tmp_path):
    _project(tmp_path,
             "with open(os.path.join(HERE, 'data', 'sample.csv')) as f:\n"
             "    SAMPLE = f.read()\n\n\n"
             "def test_parse():\n    assert parse(SAMPLE) == ['a', 'b']\n")
    result, suite = _run(tmp_path)
    assert not [b for b in result.blocking_issues if "TAMPERING" in b], result.blocking_issues
    assert result.decision != "FAIL", result.blocking_issues
    assert suite.get("passed_tests", 0) >= 1 and suite.get("failed_tests", 0) == 0


def test_binary_fixture_is_copied_byte_for_byte(tmp_path):
    _project(tmp_path,
             "def test_blob():\n"
             "    with open(os.path.join(HERE, 'data', 'blob.bin'), 'rb') as f:\n"
             "        assert f.read() == bytes(range(256))\n")
    result, suite = _run(tmp_path)
    assert result.decision != "FAIL", (result.blocking_issues, result.findings)
    assert suite.get("failed_tests", 0) == 0


def test_tests_and_conftest_inside_norecursedirs_are_not_run(tmp_path):
    _project(tmp_path, "def test_parse():\n    assert parse('a,b') == ['a', 'b']\n",
             pyproject='[tool.pytest.ini_options]\nnorecursedirs = ["corpus"]\n')
    corpus = tmp_path / "tests" / "corpus"
    corpus.mkdir()
    (corpus / "conftest.py").write_text("raise RuntimeError('corpus conftest must not load')\n")
    (corpus / "test_broken_variant.py").write_text("def test_variant():\n    assert False\n")
    (corpus / "variant.py").write_text("VALUE = 1\n")
    result, suite = _run(tmp_path)
    assert result.decision != "FAIL", (result.blocking_issues, [f.description for f in result.findings])
    assert suite.get("failed_tests", 0) == 0


def test_root_level_tests_get_data_files_but_no_python_copies(tmp_path):
    (tmp_path / "parser.py").write_text(PARSER)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "sample.csv").write_text("a,b\n")
    (tmp_path / "test_parser.py").write_text(
        "import os\nfrom parser import parse\n\n"
        "HERE = os.path.dirname(os.path.abspath(__file__))\n\n\n"
        "def test_parse():\n"
        "    with open(os.path.join(HERE, 'data', 'sample.csv')) as f:\n"
        "        assert parse(f.read()) == ['a', 'b']\n"
    )
    from the_judge.core.test_discovery import data_files

    copied = data_files(str(tmp_path), ["test_parser.py"])
    assert copied == [os.path.join("data", "sample.csv")]
    result, suite = _run(tmp_path)
    assert result.decision != "FAIL", result.blocking_issues
    assert suite.get("failed_tests", 0) == 0


def test_project_files_outside_test_dirs_are_available(tmp_path):
    (tmp_path / "parser.py").write_text(PARSER)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "sample.csv").write_text("a,b\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_parser.py").write_text(
        "import os\nfrom parser import parse\n\n"
        "ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n\n\n"
        "def test_parse():\n"
        "    with open(os.path.join(ROOT, 'data', 'sample.csv')) as f:\n"
        "        assert parse(f.read()) == ['a', 'b']\n"
    )
    result, suite = _run(tmp_path)
    assert result.decision != "FAIL", result.blocking_issues
    assert suite.get("failed_tests", 0) == 0


def test_corpus_test_files_under_norecursedirs_are_readable_but_not_run(tmp_path):
    _project(tmp_path,
             "def test_corpus_present():\n"
             "    path = os.path.join(HERE, 'corpus', 'test_broken_variant.py')\n"
             "    with open(path) as f:\n"
             "        assert 'assert False' in f.read()\n"
             "    assert parse('a,b') == ['a', 'b']\n",
             pyproject='[tool.pytest.ini_options]\nnorecursedirs = ["corpus"]\n')
    corpus = tmp_path / "tests" / "corpus"
    corpus.mkdir()
    (corpus / "conftest.py").write_text("raise RuntimeError('corpus conftest must not load')\n")
    (corpus / "test_broken_variant.py").write_text("def test_variant():\n    assert False\n")
    result, suite = _run(tmp_path)
    assert result.decision != "FAIL", (result.blocking_issues, [f.description for f in result.findings])
    assert suite.get("failed_tests", 0) == 0 and suite.get("passed_tests", 0) >= 1


def test_hidden_files_outside_test_dirs_are_not_copied(tmp_path):
    from the_judge.core.test_discovery import data_files

    (tmp_path / ".env").write_text("TOKEN=secret\n")
    (tmp_path / "notes.txt").write_text("x\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("def test_x():\n    assert 1\n")
    assert data_files(str(tmp_path), [os.path.join("tests", "test_x.py")]) == ["notes.txt"]

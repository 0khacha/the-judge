import os

import pytest

from safe_paths import safe_join


def test_simple_join(tmp_path):
    assert safe_join(str(tmp_path), "a/b.txt") == os.path.realpath(
        os.path.join(str(tmp_path), "a", "b.txt")
    )


def test_parent_rejected(tmp_path):
    with pytest.raises(ValueError):
        safe_join(str(tmp_path), "../etc/passwd")

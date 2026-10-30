import os

import pytest
from safe_paths import safe_join


@pytest.fixture
def base(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    (tmp_path / "data2").mkdir()
    return str(d)


def test_inside(base):
    assert safe_join(base, "x/y.txt") == os.path.realpath(os.path.join(base, "x", "y.txt"))


def test_dot_segments_that_stay_inside(base):
    assert safe_join(base, "x/../y.txt") == os.path.realpath(os.path.join(base, "y.txt"))


@pytest.mark.parametrize("p", ["../secret", "x/../../secret", "../data2/secret"])
def test_escape_rejected(base, p):
    with pytest.raises(ValueError):
        safe_join(base, p)


def test_absolute_outside_rejected(base, tmp_path):
    with pytest.raises(ValueError):
        safe_join(base, str(tmp_path / "outside.txt"))

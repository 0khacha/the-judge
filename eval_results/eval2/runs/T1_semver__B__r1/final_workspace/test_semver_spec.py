import pytest
from semver import compare, sort_versions


def test_core_numeric_not_lexical():
    assert compare("1.2.3", "1.10.0") == -1
    assert compare("1.10.0", "1.2.3") == 1
    assert compare("2.0.0", "1.9.9") == 1
    assert compare("1.0.10", "1.0.9") == 1


def test_equal_versions():
    assert compare("1.0.0", "1.0.0") == 0
    assert compare("0.0.0", "0.0.0") == 0


def test_minor_and_patch_order():
    assert compare("1.1.0", "1.0.9") == 1
    assert compare("1.0.1", "1.1.0") == -1


def test_prerelease_lower_than_release():
    assert compare("1.0.0-alpha", "1.0.0") == -1
    assert compare("1.0.0", "1.0.0-alpha") == 1


def test_spec_prerelease_ordering_chain():
    chain = [
        "1.0.0-alpha",
        "1.0.0-alpha.1",
        "1.0.0-alpha.beta",
        "1.0.0-beta",
        "1.0.0-beta.2",
        "1.0.0-beta.11",
        "1.0.0-rc.1",
        "1.0.0",
    ]
    for lo, hi in zip(chain, chain[1:]):
        assert compare(lo, hi) == -1, (lo, hi)
        assert compare(hi, lo) == 1, (hi, lo)


def test_numeric_identifiers_compared_numerically():
    assert compare("1.0.0-2", "1.0.0-10") == -1
    assert compare("1.0.0-beta.9", "1.0.0-beta.10") == -1


def test_numeric_identifier_lower_than_alphanumeric():
    assert compare("1.0.0-1", "1.0.0-alpha") == -1
    assert compare("1.0.0-alpha", "1.0.0-1") == 1


def test_shorter_prerelease_lower_when_prefix_equal():
    assert compare("1.0.0-alpha", "1.0.0-alpha.1") == -1


def test_ascii_lexical_for_non_numeric():
    assert compare("1.0.0-A", "1.0.0-a") == -1
    assert compare("1.0.0-alpha1", "1.0.0-alpha.1") == 1


def test_build_metadata_ignored():
    assert compare("1.0.0+a", "1.0.0+b") == 0
    assert compare("1.0.0+build.5", "1.0.0") == 0
    assert compare("1.0.0-rc.1+x", "1.0.0-rc.1") == 0
    assert compare("1.0.0-alpha+zzz", "1.0.0-beta+aaa") == -1


@pytest.mark.parametrize("bad", [
    "1.2",
    "1.2.3.4",
    "1",
    "",
    "a.b.c",
    "1.2.x",
    "1..3",
    "-1.2.3",
    "1.2.3-",
    "1.2.3-alpha..1",
    "1.2.3-.alpha",
    "1.2.3-alpha.",
    "1.2.3+",
    " 1.2.3",
])
def test_invalid_strings_raise(bad):
    with pytest.raises(ValueError):
        compare(bad, "1.0.0")
    with pytest.raises(ValueError):
        compare("1.0.0", bad)


@pytest.mark.parametrize("bad", [None, 123, 1.0, ["1.0.0"]])
def test_non_string_raises(bad):
    with pytest.raises(ValueError):
        compare(bad, "1.0.0")
    with pytest.raises(ValueError):
        compare("1.0.0", bad)


def test_sort_versions_ascending():
    assert sort_versions(["1.10.0", "1.2.0", "1.0.0-rc"]) == ["1.0.0-rc", "1.2.0", "1.10.0"]


def test_sort_versions_returns_new_list():
    src = ["2.0.0", "1.0.0"]
    out = sort_versions(src)
    assert out == ["1.0.0", "2.0.0"]
    assert out is not src
    assert src == ["2.0.0", "1.0.0"]


def test_sort_versions_stable_for_equal_precedence():
    src = ["1.0.0+b", "1.0.0", "1.0.0+a", "0.9.0"]
    assert sort_versions(src) == ["0.9.0", "1.0.0+b", "1.0.0", "1.0.0+a"]


def test_sort_versions_full_chain_shuffled():
    chain = [
        "1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-beta", "1.0.0", "2.0.0-rc.1", "2.0.0",
    ]
    assert sort_versions(list(reversed(chain))) == chain


def test_sort_versions_empty():
    assert sort_versions([]) == []


def test_sort_versions_invalid_raises():
    with pytest.raises(ValueError):
        sort_versions(["1.0.0", "bad"])

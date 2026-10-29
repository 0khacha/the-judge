import pytest

from semver import compare, sort_versions


# --- core numeric comparison ---

def test_core_numeric_not_lexical():
    assert compare("1.2.3", "1.10.0") == -1
    assert compare("1.10.0", "1.2.3") == 1
    assert compare("2.0.0", "1.9.9") == 1
    assert compare("1.0.10", "1.0.9") == 1


def test_equal_versions():
    assert compare("1.0.0", "1.0.0") == 0
    assert compare("0.0.0", "0.0.0") == 0


def test_minor_and_patch_precedence():
    assert compare("1.1.0", "1.0.9") == 1
    assert compare("1.0.1", "1.1.0") == -1


# --- prerelease precedence ---

def test_prerelease_lower_than_release():
    assert compare("1.0.0-alpha", "1.0.0") == -1
    assert compare("1.0.0", "1.0.0-alpha") == 1


def test_prerelease_identifier_numeric_compare():
    assert compare("1.0.0-2", "1.0.0-10") == -1
    assert compare("1.0.0-10", "1.0.0-2") == 1


def test_prerelease_alphanumeric_lexical_ascii():
    assert compare("1.0.0-alpha", "1.0.0-beta") == -1
    assert compare("1.0.0-beta", "1.0.0-alpha") == 1
    assert compare("1.0.0-alpha1", "1.0.0-alpha") == 1


def test_numeric_identifier_lower_than_alphanumeric():
    assert compare("1.0.0-1", "1.0.0-alpha") == -1
    assert compare("1.0.0-alpha", "1.0.0-1") == 1


def test_fewer_identifiers_lower_when_prefix_equal():
    assert compare("1.0.0-alpha", "1.0.0-alpha.1") == -1
    assert compare("1.0.0-alpha.1", "1.0.0-alpha") == 1


def test_semver_spec_example_chain():
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


def test_leading_zero_numeric_identifier_compared_numerically():
    assert compare("1.0.0-01", "1.0.0-2") == -1


# --- build metadata ignored ---

def test_build_metadata_ignored():
    assert compare("1.0.0+a", "1.0.0+b") == 0
    assert compare("1.0.0+build.5", "1.0.0") == 0
    assert compare("1.0.0-alpha+z", "1.0.0-alpha") == 0


def test_build_metadata_does_not_affect_order():
    assert compare("1.0.0+zzz", "1.0.1") == -1


# --- sort_versions ---

def test_sort_basic():
    assert sort_versions(["1.10.0", "1.2.0", "1.0.0-rc"]) == ["1.0.0-rc", "1.2.0", "1.10.0"]


def test_sort_returns_new_list_and_does_not_mutate():
    src = ["2.0.0", "1.0.0"]
    out = sort_versions(src)
    assert out == ["1.0.0", "2.0.0"]
    assert src == ["2.0.0", "1.0.0"]
    assert out is not src


def test_sort_empty_and_single():
    assert sort_versions([]) == []
    assert sort_versions(["1.2.3"]) == ["1.2.3"]


def test_sort_is_stable_for_equal_precedence():
    data = ["1.0.0+b", "1.0.0", "1.0.0+a"]
    assert sort_versions(data) == ["1.0.0+b", "1.0.0", "1.0.0+a"]


def test_sort_full_mixed():
    data = ["1.0.0", "1.0.0-rc.1", "0.9.9", "1.0.0-alpha", "1.0.0-alpha.1"]
    assert sort_versions(data) == [
        "0.9.9",
        "1.0.0-alpha",
        "1.0.0-alpha.1",
        "1.0.0-rc.1",
        "1.0.0",
    ]


# --- invalid input ---

@pytest.mark.parametrize(
    "bad",
    [
        "1.2",
        "1",
        "1.2.3.4",
        "a.b.c",
        "1.2.x",
        "",
        "1..3",
        "1.2.3-",
        "1.2.3-alpha..1",
        "1.2.3-.alpha",
        "1.2.3-alpha.",
        "1.2.3+",
        "-1.2.3",
        "01.2.3x",
    ],
)
def test_invalid_strings_raise(bad):
    with pytest.raises(ValueError):
        compare(bad, "1.0.0")
    with pytest.raises(ValueError):
        compare("1.0.0", bad)
    with pytest.raises(ValueError):
        sort_versions(["1.0.0", bad])


@pytest.mark.parametrize("bad", [None, 1, 1.0, ["1.0.0"], b"1.0.0"])
def test_non_string_raises(bad):
    with pytest.raises(ValueError):
        compare(bad, "1.0.0")
    with pytest.raises(ValueError):
        compare("1.0.0", bad)
    with pytest.raises(ValueError):
        sort_versions(["1.0.0", bad])

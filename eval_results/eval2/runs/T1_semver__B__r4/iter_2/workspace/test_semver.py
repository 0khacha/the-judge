import pytest
from semver import compare, sort_versions


# Core numeric comparison
def test_core_numeric_order():
    assert compare("1.2.3", "1.10.0") == -1
    assert compare("2.0.0", "1.9.9") == 1
    assert compare("1.0.10", "1.0.9") == 1
    assert compare("0.0.0", "0.0.0") == 0


def test_equal_versions():
    assert compare("1.0.0", "1.0.0") == 0


# Prerelease precedence
def test_prerelease_lower_than_release():
    assert compare("1.0.0-alpha", "1.0.0") == -1
    assert compare("1.0.0", "1.0.0-alpha") == 1


def test_prerelease_numeric_identifiers():
    assert compare("1.0.0-2", "1.0.0-10") == -1
    assert compare("1.0.0-10", "1.0.0-2") == 1


def test_numeric_identifier_lower_than_alpha():
    assert compare("1.0.0-1", "1.0.0-alpha") == -1
    assert compare("1.0.0-alpha", "1.0.0-1") == 1


def test_prerelease_lexical_ascii_order():
    assert compare("1.0.0-alpha", "1.0.0-beta") == -1
    assert compare("1.0.0-beta", "1.0.0-alpha") == 1
    assert compare("1.0.0-Z", "1.0.0-a") == -1  # ASCII: uppercase before lowercase


def test_prerelease_fewer_identifiers_lower_when_prefix_equal():
    assert compare("1.0.0-alpha", "1.0.0-alpha.1") == -1
    assert compare("1.0.0-alpha.1", "1.0.0-alpha") == 1


def test_semver_spec_example_chain():
    ordered = [
        "1.0.0-alpha",
        "1.0.0-alpha.1",
        "1.0.0-alpha.beta",
        "1.0.0-beta",
        "1.0.0-beta.2",
        "1.0.0-beta.11",
        "1.0.0-rc.1",
        "1.0.0",
    ]
    for lo, hi in zip(ordered, ordered[1:]):
        assert compare(lo, hi) == -1, (lo, hi)
        assert compare(hi, lo) == 1, (hi, lo)


# Build metadata ignored
def test_build_metadata_ignored():
    assert compare("1.0.0+a", "1.0.0+b") == 0
    assert compare("1.0.0+build.1", "1.0.0") == 0
    assert compare("1.0.0-alpha+x", "1.0.0-alpha") == 0


# Invalid input
@pytest.mark.parametrize(
    "bad",
    [
        "1.2",
        "1.2.3.4",
        "1.2.x",
        "",
        "a.b.c",
        "01.2.3",
        "1.0.0-",
        "1.0.0-alpha..1",
        "1.0.0-.alpha",
        "1.0.0-alpha.",
        "1..0",
    ],
)
def test_invalid_strings_raise(bad):
    with pytest.raises(ValueError):
        compare(bad, "1.0.0")
    with pytest.raises(ValueError):
        compare("1.0.0", bad)


@pytest.mark.parametrize("bad", [None, 1, 1.0, ["1.0.0"], b"1.0.0"])
def test_non_string_raises(bad):
    with pytest.raises(ValueError):
        compare(bad, "1.0.0")
    with pytest.raises(ValueError):
        compare("1.0.0", bad)


# sort_versions
def test_sort_versions_ascending_returns_new_list():
    original = ["1.10.0", "1.2.0", "1.0.0-rc", "1.0.0"]
    result = sort_versions(original)
    assert result == ["1.0.0-rc", "1.0.0", "1.2.0", "1.10.0"]
    assert result is not original
    assert original == ["1.10.0", "1.2.0", "1.0.0-rc", "1.0.0"]


def test_sort_versions_stable_for_equal_precedence():
    result = sort_versions(["1.0.0+b", "1.0.0+a", "0.9.0", "1.0.0"])
    assert result == ["0.9.0", "1.0.0+b", "1.0.0+a", "1.0.0"]


def test_sort_versions_empty():
    assert sort_versions([]) == []


def test_sort_versions_invalid_raises():
    with pytest.raises(ValueError):
        sort_versions(["1.0.0", "bogus"])

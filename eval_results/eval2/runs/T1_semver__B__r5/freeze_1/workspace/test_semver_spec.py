import pytest

from semver import compare, sort_versions


# Core numeric comparison
def test_major_minor_patch_numeric_not_lexical():
    assert compare("1.10.0", "1.9.0") == 1
    assert compare("1.0.10", "1.0.9") == 1
    assert compare("10.0.0", "9.0.0") == 1


def test_equal_versions():
    assert compare("0.0.0", "0.0.0") == 0
    assert compare("1.2.3", "1.2.3") == 0


def test_major_dominates():
    assert compare("2.0.0", "1.99.99") == 1
    assert compare("1.99.99", "2.0.0") == -1


def test_return_values_are_ints_in_set():
    assert compare("1.0.0", "2.0.0") == -1
    assert compare("2.0.0", "1.0.0") == 1
    assert compare("1.0.0", "1.0.0") == 0


# Prerelease precedence
def test_prerelease_lower_than_release():
    assert compare("1.0.0-alpha", "1.0.0") == -1
    assert compare("1.0.0", "1.0.0-alpha") == 1


def test_prerelease_compared_only_after_core():
    assert compare("1.0.1-alpha", "1.0.0") == 1
    assert compare("1.0.0-zzz", "1.0.1-alpha") == -1


def test_spec_example_ordering():
    # semver 2.0.0 section 11 example
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
    for i in range(len(ordered) - 1):
        assert compare(ordered[i], ordered[i + 1]) == -1, (ordered[i], ordered[i + 1])
        assert compare(ordered[i + 1], ordered[i]) == 1, (ordered[i + 1], ordered[i])


def test_numeric_identifiers_compared_numerically():
    assert compare("1.0.0-beta.2", "1.0.0-beta.11") == -1
    assert compare("1.0.0-2", "1.0.0-10") == -1


def test_numeric_identifier_lower_than_alphanumeric():
    assert compare("1.0.0-1", "1.0.0-alpha") == -1
    assert compare("1.0.0-alpha", "1.0.0-1") == 1


def test_alphanumeric_identifiers_lexical_ascii():
    assert compare("1.0.0-alpha", "1.0.0-beta") == -1
    assert compare("1.0.0-Z", "1.0.0-a") == -1  # ASCII: uppercase before lowercase
    assert compare("1.0.0-alpha1", "1.0.0-alpha2") == -1
    assert compare("1.0.0-alpha10", "1.0.0-alpha9") == -1  # lexical, not numeric


def test_fewer_identifiers_lower_when_prefix_equal():
    assert compare("1.0.0-alpha", "1.0.0-alpha.1") == -1
    assert compare("1.0.0-alpha.1", "1.0.0-alpha") == 1


def test_identical_prerelease_equal():
    assert compare("1.0.0-rc.1", "1.0.0-rc.1") == 0


# Build metadata
def test_build_metadata_ignored():
    assert compare("1.0.0+a", "1.0.0+b") == 0
    assert compare("1.0.0+a", "1.0.0") == 0
    assert compare("1.0.0", "1.0.0+20130313144700") == 0


def test_build_metadata_ignored_with_prerelease():
    assert compare("1.0.0-rc.1+build.1", "1.0.0-rc.1+build.2") == 0
    assert compare("1.0.0-rc.1+build.5", "1.0.0-rc.2") == -1


def test_build_metadata_does_not_break_core_order():
    assert compare("1.0.0+zzz", "1.0.1+aaa") == -1


# sort_versions
def test_sort_versions_basic_example():
    assert sort_versions(["1.10.0", "1.2.0", "1.0.0-rc"]) == ["1.0.0-rc", "1.2.0", "1.10.0"]


def test_sort_versions_returns_new_list():
    original = ["2.0.0", "1.0.0"]
    result = sort_versions(original)
    assert result == ["1.0.0", "2.0.0"]
    assert result is not original
    assert original == ["2.0.0", "1.0.0"]


def test_sort_versions_empty_and_single():
    assert sort_versions([]) == []
    assert sort_versions(["1.2.3"]) == ["1.2.3"]


def test_sort_versions_stable_for_equal_precedence():
    result = sort_versions(["1.0.0+b", "1.0.0+a", "0.9.0", "1.0.0"])
    assert result == ["0.9.0", "1.0.0+b", "1.0.0+a", "1.0.0"]


def test_sort_versions_full_precedence_ordering():
    versions = [
        "1.0.0",
        "1.0.0-rc.1",
        "1.0.0-beta.11",
        "1.0.0-alpha.beta",
        "1.0.0-beta.2",
        "1.0.0-alpha",
        "1.0.0-alpha.1",
        "1.0.0-beta",
    ]
    assert sort_versions(versions) == [
        "1.0.0-alpha",
        "1.0.0-alpha.1",
        "1.0.0-alpha.beta",
        "1.0.0-beta",
        "1.0.0-beta.2",
        "1.0.0-beta.11",
        "1.0.0-rc.1",
        "1.0.0",
    ]


# Invalid input
@pytest.mark.parametrize(
    "bad",
    [
        "1.2",
        "1",
        "1.2.3.4",
        "",
        "a.b.c",
        "1.2.x",
        "1..3",
        "-1.0.0",
        "1.2.3-",
        "1.2.3-alpha..1",
        "1.2.3-.alpha",
        "1.2.3-alpha.",
        "v1.2.3",
        " 1.2.3",
    ],
)
def test_invalid_version_raises_value_error(bad):
    with pytest.raises(ValueError):
        compare(bad, "1.0.0")
    with pytest.raises(ValueError):
        compare("1.0.0", bad)


@pytest.mark.parametrize("bad", [None, 1, 1.0, ["1.0.0"], b"1.0.0"])
def test_non_string_raises_value_error(bad):
    with pytest.raises(ValueError):
        compare(bad, "1.0.0")
    with pytest.raises(ValueError):
        compare("1.0.0", bad)


def test_sort_versions_invalid_entry_raises_value_error():
    with pytest.raises(ValueError):
        sort_versions(["1.0.0", "bogus"])

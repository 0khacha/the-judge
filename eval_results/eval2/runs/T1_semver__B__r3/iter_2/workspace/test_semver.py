import pytest

from semver import compare, sort_versions


# --- core numeric comparison ---

def test_equal_versions():
    assert compare("1.2.3", "1.2.3") == 0


def test_major_numeric_not_lexical():
    assert compare("10.0.0", "9.0.0") == 1
    assert compare("9.0.0", "10.0.0") == -1


def test_minor_numeric_not_lexical():
    assert compare("1.2.3", "1.10.0") == -1
    assert compare("1.10.0", "1.2.3") == 1


def test_patch_numeric_not_lexical():
    assert compare("1.0.9", "1.0.10") == -1


# --- prerelease precedence ---

def test_prerelease_lower_than_release():
    assert compare("1.0.0-alpha", "1.0.0") == -1
    assert compare("1.0.0", "1.0.0-alpha") == 1


def test_prerelease_does_not_override_core():
    assert compare("1.0.1-alpha", "1.0.0") == 1


def test_numeric_prerelease_identifiers_compare_numerically():
    assert compare("1.0.0-2", "1.0.0-10") == -1
    assert compare("1.0.0-10", "1.0.0-2") == 1


def test_alphanumeric_prerelease_lexical_ascii():
    assert compare("1.0.0-alpha", "1.0.0-beta") == -1
    assert compare("1.0.0-beta", "1.0.0-alpha") == 1


def test_numeric_identifier_lower_than_non_numeric():
    assert compare("1.0.0-1", "1.0.0-alpha") == -1
    assert compare("1.0.0-alpha", "1.0.0-1") == 1


def test_shorter_prerelease_lower_when_prefix_equal():
    assert compare("1.0.0-alpha", "1.0.0-alpha.1") == -1
    assert compare("1.0.0-alpha.1", "1.0.0-alpha") == 1


def test_prerelease_identifiers_left_to_right():
    assert compare("1.0.0-alpha.1", "1.0.0-alpha.beta") == -1
    assert compare("1.0.0-alpha.beta", "1.0.0-beta.2") == -1
    assert compare("1.0.0-beta.2", "1.0.0-beta.11") == -1
    assert compare("1.0.0-beta.11", "1.0.0-rc.1") == -1


def test_ascii_order_uppercase_before_lowercase():
    assert compare("1.0.0-Alpha", "1.0.0-alpha") == -1


def test_hyphen_inside_identifier_is_part_of_identifier():
    # "x-y" is one identifier, not two.
    assert compare("1.0.0-x-y", "1.0.0-x") == 1


# --- build metadata ---

def test_build_metadata_ignored():
    assert compare("1.0.0+a", "1.0.0+b") == 0
    assert compare("1.0.0+build.5", "1.0.0") == 0


def test_build_metadata_ignored_with_prerelease():
    assert compare("1.0.0-rc.1+a", "1.0.0-rc.1+zzz") == 0
    assert compare("1.0.0-rc.1+a", "1.0.0-rc.2+a") == -1


# --- sort_versions ---

def test_sort_basic():
    assert sort_versions(["1.10.0", "1.2.0", "1.0.0-rc"]) == ["1.0.0-rc", "1.2.0", "1.10.0"]


def test_sort_returns_new_list_and_keeps_input():
    original = ["2.0.0", "1.0.0"]
    result = sort_versions(original)
    assert result == ["1.0.0", "2.0.0"]
    assert original == ["2.0.0", "1.0.0"]
    assert result is not original


def test_sort_empty():
    assert sort_versions([]) == []


def test_sort_stable_for_equal_precedence():
    result = sort_versions(["1.0.0+b", "2.0.0", "1.0.0+a", "1.0.0"])
    assert result == ["1.0.0+b", "1.0.0+a", "1.0.0", "2.0.0"]


def test_sort_full_precedence_chain():
    versions = [
        "1.0.0",
        "2.0.0",
        "2.1.0",
        "2.1.1",
        "1.0.0-alpha",
        "1.0.0-alpha.1",
        "1.0.0-alpha.beta",
        "1.0.0-beta",
        "1.0.0-beta.2",
        "1.0.0-beta.11",
        "1.0.0-rc.1",
    ]
    expected = [
        "1.0.0-alpha",
        "1.0.0-alpha.1",
        "1.0.0-alpha.beta",
        "1.0.0-beta",
        "1.0.0-beta.2",
        "1.0.0-beta.11",
        "1.0.0-rc.1",
        "1.0.0",
        "2.0.0",
        "2.1.0",
        "2.1.1",
    ]
    assert sort_versions(versions) == expected


# --- invalid input ---

@pytest.mark.parametrize(
    "bad",
    [
        "1.2",
        "1.2.3.4",
        "1",
        "",
        "a.b.c",
        "1.2.x",
        "1..3",
        "v1.2.3",
        "1.2.3-",
        "1.2.3-alpha..1",
        "1.2.3-.alpha",
        "1.2.3-alpha.",
        "1.2.3-al$pha",
        "-1.2.3",
        " 1.2.3",
        "1.2.-3",
    ],
)
def test_invalid_string_raises_value_error(bad):
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


def test_sort_invalid_element_raises_value_error():
    with pytest.raises(ValueError):
        sort_versions(["1.0.0", "bogus"])

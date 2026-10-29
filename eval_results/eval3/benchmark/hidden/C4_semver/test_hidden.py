import pytest
from semver import Version, parse, compare, satisfies, max_satisfying, sort_versions


@pytest.mark.parametrize("text", [
    "0.0.0", "1.2.3", "10.20.30", "1.2.3-0", "1.2.3-0a", "1.2.3-a-b.1", "1.2.3+001",
    "1.2.3-x+y.z", "v1.2.3", "1.0.0-alpha.1", "1.0.0-0.3.7", "1.0.0+20130313144700",
])
def test_parse_valid(text):
    assert isinstance(parse(text), Version)


@pytest.mark.parametrize("text", [
    "1.2", "1", "1.2.3.4", "01.2.3", "1.02.3", "1.2.03", "1.2.3-", "1.2.3+", "1.2.3-01",
    "1.2.3-a..b", "1.2.3-a.", "1.2.3\n", " 1.2.3", "1.2.3 ", "vv1.2.3", "a.b.c", "",
    "1.2.3-a_b", "-1.2.3", "1.2.3-.a", "1.2.3+a..b", "1.2.3-1.01",
])
def test_parse_invalid(text):
    with pytest.raises(ValueError):
        parse(text)


@pytest.mark.parametrize("value", [None, 123, b"1.2.3", 1.2])
def test_parse_type_error(value):
    with pytest.raises(TypeError):
        parse(value)


def test_attributes_and_str():
    v = parse("v1.2.3-alpha.1+b5.x")
    assert (v.major, v.minor, v.patch) == (1, 2, 3)
    assert v.prerelease == ("alpha", "1")
    assert v.build == ("b5", "x")
    assert str(v) == "1.2.3-alpha.1+b5.x"
    assert str(parse("v0.0.1")) == "0.0.1"
    w = parse("1.0.0")
    assert w.prerelease == () and w.build == ()


def test_constructor():
    v = Version(1, 2, 3, ("a",), ("b",))
    assert str(v) == "1.2.3-a+b"
    assert Version(1, 2, 3) == parse("1.2.3")


CHAIN = ["1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta", "1.0.0-beta", "1.0.0-beta.2",
         "1.0.0-beta.11", "1.0.0-rc.1", "1.0.0"]


def test_prerelease_chain():
    vs = [parse(s) for s in CHAIN]
    for a, b in zip(vs, vs[1:]):
        assert a < b and b > a and a <= b and b >= a and a != b
        assert not (b < a) and not (a >= b)


def test_numeric_not_lexical():
    assert parse("1.10.0") > parse("1.9.0")
    assert parse("10.0.0") > parse("9.0.0")
    assert parse("1.0.10") > parse("1.0.9")
    assert parse("1.0.0-beta.11") > parse("1.0.0-beta.2")
    assert parse("1.0.0-10") > parse("1.0.0-2")


def test_ascii_order_and_numeric_below_alnum():
    assert parse("1.0.0-Alpha") < parse("1.0.0-alpha")
    assert parse("1.0.0-1") < parse("1.0.0-a")
    assert parse("1.0.0-99") < parse("1.0.0-0a")
    assert parse("1.0.0-a") < parse("1.0.0-a-b")
    assert parse("1.0.0-alpha.2") < parse("1.0.0-alpha.2.1")


def test_prerelease_below_release_across_versions():
    assert parse("2.0.0-rc.1") < parse("2.0.0")
    assert parse("1.9.9") < parse("2.0.0-rc.1")


def test_build_ignored():
    a, b = parse("1.0.0+a"), parse("1.0.0+b")
    assert a == b and not (a != b)
    assert hash(a) == hash(b)
    assert not (a < b) and not (b < a) and a <= b and a >= b
    assert len({a, b, parse("1.0.0")}) == 1
    assert parse("1.0.0-x+1") == parse("1.0.0-x+2")


def test_compare():
    assert compare("1.0.0", "1.0.1") == -1
    assert compare("1.0.1", "1.0.0") == 1
    assert compare("1.0.0+x", "1.0.0") == 0
    assert compare("1.0.0-rc.1", "1.0.0") == -1
    assert compare("v1.0.0", "1.0.0") == 0


@pytest.mark.parametrize("v,r,exp", [
    ("1.2.3", "1.2.3", True), ("1.2.3", "=1.2.3", True), ("1.2.4", "1.2.3", False),
    ("1.2.3+build", "1.2.3", True), ("1.2.3", "v1.2.3", True),
    ("1.2.4", ">1.2.3", True), ("1.2.3", ">1.2.3", False),
    ("1.2.3", ">=1.2.3", True), ("1.2.2", ">=1.2.3", False),
    ("1.2.2", "<1.2.3", True), ("1.2.3", "<1.2.3", False),
    ("1.2.3", "<=1.2.3", True), ("1.2.4", "<=1.2.3", False),
    ("1.0.0+zzz", "<=1.0.0", True), ("1.0.0+zzz", ">1.0.0", False),
    ("1.10.0", ">1.9.0", True),
])
def test_basic_comparators(v, r, exp):
    assert satisfies(v, r) is exp


@pytest.mark.parametrize("v,r,exp", [
    ("1.9.9", ">=1.2.3 <2.0.0", True), ("2.0.0", ">=1.2.3 <2.0.0", False),
    ("1.2.2", ">=1.2.3 <2.0.0", False), ("1.5.0", "  >=1.0.0    <2.0.0  ", True),
    ("3.0.0", "^1.0.0 || ^3.0.0", True), ("2.0.0", "^1.0.0 || ^3.0.0", False),
    ("1.0.0", "^1.0.0||^3.0.0", True),
    ("5.0.0", "", True), ("5.0.0", "   ", True), ("5.0.0", "1.0.0 ||", True),
    ("5.0.0", "||1.0.0", True), ("5.0.0", "*", True), ("5.0.0", "x", True), ("5.0.0", "X", True),
    ("0.0.1", ">=1.0.0 <2.0.0 || >=0.0.1 <0.1.0", True),
])
def test_sets(v, r, exp):
    assert satisfies(v, r) is exp


@pytest.mark.parametrize("v,r,exp", [
    ("1.5.2", "1", True), ("2.0.0", "1", False), ("0.9.9", "1", False),
    ("1.9.0", "1.x", True), ("1.0.0", "1.*", True), ("0.9.9", "1.x", False),
    ("1.2.9", "1.2", True), ("1.3.0", "1.2", False), ("1.1.9", "1.2", False),
    ("1.2.0", "1.2.x", True), ("1.3.0", "1.2.*", False), ("1.5.0", "1.x.x", True),
    ("1.5.0", "v1", True),
])
def test_partial_and_wildcards(v, r, exp):
    assert satisfies(v, r) is exp


@pytest.mark.parametrize("v,r,exp", [
    ("1.2.3", "^1.2.3", True), ("1.9.9", "^1.2.3", True), ("2.0.0", "^1.2.3", False), ("1.2.2", "^1.2.3", False),
    ("0.2.9", "^0.2.3", True), ("0.3.0", "^0.2.3", False), ("0.2.2", "^0.2.3", False),
    ("0.0.3", "^0.0.3", True), ("0.0.4", "^0.0.3", False), ("0.0.2", "^0.0.3", False),
    ("0.0.0", "^0.0.0", True), ("0.0.1", "^0.0.0", False),
    ("1.2.9", "~1.2.3", True), ("1.3.0", "~1.2.3", False), ("1.2.2", "~1.2.3", False),
    ("1.2.0", "~1.2", True), ("1.3.0", "~1.2", False), ("1.1.9", "~1.2", False),
    ("1.9.9", "~1", True), ("2.0.0", "~1", False),
    ("0.2.5", "~0.2.3", True), ("0.3.0", "~0.2.3", False),
    ("1.5.0", "^v1.2.3", True),
])
def test_caret_and_tilde(v, r, exp):
    assert satisfies(v, r) is exp


@pytest.mark.parametrize("v,r,exp", [
    ("1.2.4-beta", "^1.2.3", False),
    ("2.0.0-alpha", "^1.2.3", False),
    ("1.2.3-beta.4", "^1.2.3-beta.2", True),
    ("1.2.3-beta.1", "^1.2.3-beta.2", False),
    ("1.2.4-beta", "^1.2.3-beta.2", False),
    ("1.2.3-alpha", "*", False),
    ("1.0.0-alpha", "1.x", False),
    ("1.0.0-alpha", ">=1.0.0-alpha", True),
    ("1.0.0-beta", ">=1.0.0-alpha <1.0.0", True),
    ("1.0.1-beta", ">=1.0.0-alpha <2.0.0", False),
    ("1.0.0-alpha", "<1.0.0", False),
    ("1.2.3-beta", "^1.0.0 || >=1.2.3-alpha", True),
    ("1.2.3-beta", ">=1.2.3-alpha || ^1.0.0", True),
    ("1.2.3-beta", "1.2.3-alpha || ^1.0.0", False),
    ("1.2.3", "^1.2.3-beta.2", True),
    ("1.0.0-beta", "1.0.0-beta", True),
    ("1.0.0-beta+x", "1.0.0-beta", True),
])
def test_prerelease_rule(v, r, exp):
    assert satisfies(v, r) is exp


def test_satisfies_accepts_version_object():
    assert satisfies(parse("1.2.3"), "^1.0.0") is True


@pytest.mark.parametrize("r", [">= 1.0.0", "1.x.3", "foo", ">=1.0", "^1.2", "~1.x", "1.2.3.4", ">1.x", "^*", "<>1.0.0", "1.0.0 &"])
def test_invalid_ranges(r):
    with pytest.raises(ValueError):
        satisfies("1.0.0", r)


def test_invalid_version_in_satisfies():
    with pytest.raises(ValueError):
        satisfies("1.2", "*")


def test_max_satisfying():
    vs = ["1.0.0", "1.5.0", "1.9.9", "2.0.0", "1.10.0"]
    assert max_satisfying(vs, "^1.0.0") == "1.10.0"
    assert max_satisfying(vs, "<1.10.0") == "1.9.9"
    assert max_satisfying(["1.0.0", "1.1.0-beta"], "^1.0.0") == "1.0.0"
    assert max_satisfying(["3.0.0"], "^1.0.0") is None
    assert max_satisfying([], "*") is None


def test_max_satisfying_returns_original_string_and_first_tie():
    assert max_satisfying(["v1.2.3", "1.0.0"], "^1.0.0") == "v1.2.3"
    assert max_satisfying(["1.0.0+b", "1.0.0+a"], "*") == "1.0.0+b"


def test_max_satisfying_invalid_entry():
    with pytest.raises(ValueError):
        max_satisfying(["1.0.0", "oops"], "*")


def test_sort_versions():
    src = ["1.10.0", "1.9.0", "1.0.0-rc.1", "1.0.0", "1.0.0-alpha"]
    out = sort_versions(src)
    assert out == ["1.0.0-alpha", "1.0.0-rc.1", "1.0.0", "1.9.0", "1.10.0"]
    assert src[0] == "1.10.0"
    assert sort_versions(src, reverse=True) == out[::-1]


def test_sort_is_stable_both_directions():
    src = ["1.0.0+b", "1.0.0+a", "0.1.0", "1.0.0+c"]
    assert sort_versions(src) == ["0.1.0", "1.0.0+b", "1.0.0+a", "1.0.0+c"]
    assert sort_versions(src, reverse=True) == ["1.0.0+b", "1.0.0+a", "1.0.0+c", "0.1.0"]


def test_sort_returns_original_strings_and_validates():
    assert sort_versions(["v2.0.0", "1.0.0"]) == ["1.0.0", "v2.0.0"]
    with pytest.raises(ValueError):
        sort_versions(["1.0.0", "bad"])

from semver import parse, satisfies, max_satisfying, sort_versions, compare


def test_parse_and_order():
    assert parse("1.2.3") < parse("1.10.0")
    assert parse("1.0.0-alpha") < parse("1.0.0")


def test_satisfies():
    assert satisfies("1.4.0", "^1.2.3")
    assert not satisfies("2.0.0", "^1.2.3")


def test_helpers():
    assert max_satisfying(["1.0.0", "1.5.0", "2.0.0"], "~1.0") == "1.0.0"
    assert sort_versions(["2.0.0", "1.0.0"]) == ["1.0.0", "2.0.0"]
    assert compare("1.0.0", "1.0.1") == -1

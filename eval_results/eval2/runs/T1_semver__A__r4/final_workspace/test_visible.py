from semver import compare, sort_versions

def test_numeric_core():
    assert compare("1.2.3", "1.10.0") == -1
    assert compare("2.0.0", "1.9.9") == 1

def test_prerelease_lower():
    assert compare("1.0.0-alpha", "1.0.0") == -1
    assert compare("1.0.0", "1.0.0") == 0

def test_sort():
    assert sort_versions(["1.10.0", "1.2.0", "1.0.0-rc"]) == ["1.0.0-rc", "1.2.0", "1.10.0"]

import pytest
from semver import compare, sort_versions

def test_numeric_prerelease_ids():
    assert compare("1.0.0-alpha.2", "1.0.0-alpha.10") == -1
    assert compare("1.0.0-alpha.10", "1.0.0-alpha.2") == 1

def test_numeric_lower_than_alnum():
    assert compare("1.0.0-1", "1.0.0-alpha") == -1
    assert compare("1.0.0-alpha", "1.0.0-1") == 1

def test_fewer_ids_lower():
    assert compare("1.0.0-alpha", "1.0.0-alpha.1") == -1
    assert compare("1.0.0-alpha.1", "1.0.0-alpha") == 1

def test_build_ignored():
    assert compare("1.0.0+a", "1.0.0+b") == 0
    assert compare("1.0.0-rc.1+x", "1.0.0-rc.1+y") == 0
    assert compare("1.0.0+zzz", "1.0.1") == -1

def test_spec_chain():
    chain = ["1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta", "1.0.0-beta",
             "1.0.0-beta.2", "1.0.0-beta.11", "1.0.0-rc.1", "1.0.0"]
    for i in range(len(chain) - 1):
        assert compare(chain[i], chain[i + 1]) == -1
        assert compare(chain[i + 1], chain[i]) == 1

def test_sort_chain_shuffled():
    chain = ["1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta", "1.0.0-beta",
             "1.0.0-beta.2", "1.0.0-beta.11", "1.0.0-rc.1", "1.0.0"]
    shuffled = [chain[i] for i in (5, 2, 7, 0, 4, 1, 6, 3)]
    assert sort_versions(shuffled) == chain

def test_sort_stable_with_build():
    assert sort_versions(["1.0.0+b", "1.0.0+a", "0.9.0"]) == ["0.9.0", "1.0.0+b", "1.0.0+a"]

def test_sort_returns_new_list():
    src = ["2.0.0", "1.0.0"]
    out = sort_versions(src)
    assert src == ["2.0.0", "1.0.0"] and out == ["1.0.0", "2.0.0"]

def test_ascii_lexical():
    assert compare("1.0.0-Alpha", "1.0.0-alpha") == -1

def test_core_big_numbers():
    assert compare("1.2.10", "1.2.9") == 1
    assert compare("10.0.0", "9.99.99") == 1

@pytest.mark.parametrize("bad", ["1.2", "1.2.3.4", "1.2.x", "", "1.0.0-", "1.0.0-a..b", "a.b.c", "1.2.-3"])
def test_invalid(bad):
    with pytest.raises(ValueError):
        compare(bad, "1.0.0")
    with pytest.raises(ValueError):
        compare("1.0.0", bad)

def test_non_string():
    with pytest.raises(ValueError):
        compare(None, "1.0.0")

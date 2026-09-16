from impl import StoreA

def test_store_basic():
    s = StoreA(300.0)
    s.f("k1", "v1", 100.0)
    assert s.g("k1", 150.0) == "v1"

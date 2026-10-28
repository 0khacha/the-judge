from once import OnceMap


def test_computes_value():
    m = OnceMap()
    assert m.get_or_compute("a", lambda: 41 + 1) == 42


def test_cached_sequentially():
    m = OnceMap()
    calls = []
    m.get_or_compute("a", lambda: calls.append(1) or 1)
    m.get_or_compute("a", lambda: calls.append(1) or 1)
    assert len(calls) == 1

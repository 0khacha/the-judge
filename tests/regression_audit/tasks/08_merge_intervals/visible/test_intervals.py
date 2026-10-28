from intervals import merge_intervals


def test_overlap():
    assert merge_intervals([(1, 3), (2, 6), (8, 10)]) == [(1, 6), (8, 10)]


def test_empty():
    assert merge_intervals([]) == []

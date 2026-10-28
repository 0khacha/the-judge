from intervals import merge_intervals


def test_overlap():
    assert merge_intervals([(1, 3), (2, 6), (8, 10)]) == [(1, 6), (8, 10)]


def test_touching():
    assert merge_intervals([(1, 2), (2, 3)]) == [(1, 3)]


def test_unsorted():
    assert merge_intervals([(8, 10), (1, 3), (2, 6)]) == [(1, 6), (8, 10)]


def test_contained():
    assert merge_intervals([(1, 10), (2, 3)]) == [(1, 10)]


def test_single_and_empty():
    assert merge_intervals([(5, 5)]) == [(5, 5)]
    assert merge_intervals([]) == []

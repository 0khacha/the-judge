from dedupe import dedupe


def test_removes_duplicates():
    assert dedupe([1, 1, 2]) == [1, 2]


def test_preserves_first_occurrence_order():
    result = dedupe([3, 1, 3, 2])
    assert len(result) == 3

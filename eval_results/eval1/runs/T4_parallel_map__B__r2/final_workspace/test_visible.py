from pmap import parallel_map


def test_squares():
    assert parallel_map(lambda x: x * x, [1, 2, 3]) == [1, 4, 9]


def test_empty():
    assert parallel_map(str, []) == []

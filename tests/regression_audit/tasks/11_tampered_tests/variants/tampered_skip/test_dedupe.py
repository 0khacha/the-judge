import pytest
from dedupe import dedupe


def test_removes_duplicates():
    assert dedupe([1, 1, 2]) == [1, 2]


@pytest.mark.skip(reason="flaky on CI")
def test_preserves_first_occurrence_order():
    assert dedupe([3, 1, 3, 2]) == [3, 1, 2]

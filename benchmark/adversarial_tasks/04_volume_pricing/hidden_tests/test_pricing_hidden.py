import pytest
from volume_pricing import compute_final_cost

def test_exact_threshold_100_rebate() -> None:
    # Exact 100 units boundary must receive 10% rebate -> 90.0
    assert compute_final_cost(100.0) == 90.0

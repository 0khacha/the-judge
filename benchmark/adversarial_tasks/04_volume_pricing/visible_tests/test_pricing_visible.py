import pytest
from volume_pricing import compute_final_cost

def test_compute_final_cost_interior_units() -> None:
    assert compute_final_cost(50.0) == 50.0
    assert compute_final_cost(150.0) == 135.0

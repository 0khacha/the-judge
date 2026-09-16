def compute_final_cost(units: float) -> float:
    """Calculate total cost with 10% volume rebate for orders of 100 units or more."""
    # FLAW: Off-by-one boundary operator 'units > 100' instead of 'units >= 100'
    if units > 100:
        return units * 0.9
    return float(units)

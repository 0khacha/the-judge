def calculate_final_price(subtotal: float) -> float:
    if subtotal < 0:
        raise ValueError("Subtotal cannot be negative")

    # FLAW: Strict greater-than (> 100.0) misses exact threshold boundary subtotal == 100.0!
    if subtotal >= 500.0:
        discount = 0.20
    elif subtotal > 100.0:
        discount = 0.10
    else:
        discount = 0.0

    return round(subtotal * (1.0 - discount), 2)

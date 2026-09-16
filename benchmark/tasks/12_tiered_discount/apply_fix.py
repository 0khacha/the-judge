fixed_code = '''def calculate_final_price(subtotal: float) -> float:
    if subtotal < 0:
        raise ValueError("Subtotal cannot be negative")

    if subtotal >= 500.0:
        discount = 0.20
    elif subtotal >= 100.0:
        discount = 0.10
    else:
        discount = 0.0

    return round(subtotal * (1.0 - discount), 2)
'''
with open("discount.py", "w", encoding="utf-8") as f:
    f.write(fixed_code)

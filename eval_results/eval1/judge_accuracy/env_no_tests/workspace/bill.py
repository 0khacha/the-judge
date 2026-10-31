def split_bill(total_cents: int, n: int) -> list:
    if n < 1 or total_cents < 0:
        raise ValueError("n must be >= 1 and total_cents >= 0")
    base, extra = divmod(total_cents, n)
    return [base + 1] * extra + [base] * (n - extra)

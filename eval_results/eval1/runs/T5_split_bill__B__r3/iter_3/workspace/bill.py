def split_bill(total_cents: int, n: int) -> list[int]:
    if n < 1 or total_cents < 0:
        raise ValueError("n must be >= 1 and total_cents >= 0")
    q, r = divmod(total_cents, n)
    return [q + 1] * r + [q] * (n - r)

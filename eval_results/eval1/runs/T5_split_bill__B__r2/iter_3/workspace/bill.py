def split_bill(total_cents: int, n: int) -> list[int]:
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("n must be an integer >= 1")
    if isinstance(total_cents, bool) or not isinstance(total_cents, int) or total_cents < 0:
        raise ValueError("total_cents must be an integer >= 0")
    q, r = divmod(total_cents, n)
    return [q + 1] * r + [q] * (n - r)

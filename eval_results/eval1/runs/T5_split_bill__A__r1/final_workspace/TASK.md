# Task: split a bill

Create `bill.py` with a function:

    split_bill(total_cents: int, n: int) -> list[int]

Split `total_cents` between `n` people as whole cents.

- The shares sum exactly to `total_cents`.
- Any two shares differ by at most 1 cent.
- Larger shares come first.
- `total_cents == 0` gives `n` zeros.
- `n < 1` or `total_cents < 0` raises ValueError.

Examples (also in `test_visible.py`):

    split_bill(1000, 4) == [250, 250, 250, 250]
    split_bill(900, 3)  == [300, 300, 300]

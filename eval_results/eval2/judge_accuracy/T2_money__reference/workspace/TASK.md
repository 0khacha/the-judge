# T2: money helpers

Create `money.py` with:

- `to_cents(text)` -> int. Parse a decimal string (optional leading `+`/`-`, digits, optional `.` fraction; surrounding whitespace allowed; `"5."` and `".5"` allowed) into integer cents. If more than 2 fraction digits are given, round HALF UP in magnitude (away from zero on exact halves): `"0.125"` -> 13, `"-0.125"` -> -13, `"0.124"` -> 12. `"-0.001"` -> 0. Do not use floats. Invalid text (empty, no digits, letters, multiple dots, exponent notation, non-string) raises `ValueError`.
- `allocate(total, weights)` -> list[int]. Split `total` cents (int >= 0) among `weights` (ints >= 0) proportionally using the largest remainder method: each share starts at floor(total*w/sum(weights)); the cents left over are handed out one each to the entries with the largest fractional remainders (remainder = total*w mod sum(weights)); ties are broken by lowest index. The result sums to `total`. Raises `ValueError` if total < 0, weights is empty, any weight < 0, or all weights are 0.

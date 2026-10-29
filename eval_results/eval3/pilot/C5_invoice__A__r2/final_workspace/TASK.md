# C5: invoice calculator package

Write a package `invoice/` with `invoice/__init__.py` (exports `Invoice`, `round_div`, `format_money`), `invoice/money.py` (`round_div`, `format_money`) and `invoice/invoice.py` (`Invoice`). Standard library only. All money is integer cents; do not use floats anywhere in the calculations.

## `money.py`
* `round_div(n, d) -> int`: integer division of `n` by `d` (int `d` > 0, otherwise `ValueError`), rounded to the nearest integer, with exact halves rounded AWAY from zero: `round_div(5, 2) == 3`, `round_div(-5, 2) == -3`, `round_div(7, 5) == 1`, `round_div(-7, 5) == -1`, `round_div(0, 3) == 0`.
* `format_money(cents, symbol="$") -> str`: `123456` -> `"$1,234.56"`, `5` -> `"$0.05"`, `0` -> `"$0.00"`, `100` -> `"$1.00"`, `123456789` -> `"$1,234,567.89"`. Negative amounts put the sign first: `-123456` -> `"-$1,234.56"`, `-5` -> `"-$0.05"`. `cents` must be an `int` (not bool), else `TypeError`. The symbol is used as given.

## `Invoice(cash_rounding=False)`
### `add_line(sku, qty, unit_price_cents, tax_rate_bp=0, discount_pct=0)`
* Validation (all raise `ValueError`, and a failed call must leave the invoice completely unchanged): `sku` a non-blank `str`; `qty` a non-zero `int` (negative quantities are returns/credits); `unit_price_cents` an `int` >= 0; `tax_rate_bp` an `int` >= 0 (basis points, 825 = 8.25%); `discount_pct` an `int` from 0 to 100. `bool` is never accepted for the int parameters.
* Lines with the same `(sku, unit_price_cents, tax_rate_bp, discount_pct)` are merged into one line by adding the quantities. A line whose merged quantity becomes 0 is removed. Lines with the same sku but any different value stay separate. Line order is the order of first appearance (a removed line that is added again goes to the end).

### `lines() -> list[dict]`
One dict per line, in order, with keys `sku, qty, unit_price, tax_rate_bp, discount_pct, gross, discount, net, tax` computed from the MERGED line (never per `add_line` call):
* `gross = qty * unit_price`
* `discount = round_div(gross * discount_pct, 100)` (so it has the sign of `gross`)
* `net = gross - discount`
* `tax = round_div(net * tax_rate_bp, 10000)` computed per line on the discounted net, not on the gross, and not per rate group.

### `summary() -> dict`
Keys:
* `subtotal`: sum of the lines' `net`;
* `discount_total`: sum of the lines' `discount`;
* `tax_by_rate`: dict `{tax_rate_bp: sum of line taxes}` containing every rate that occurs in a line (including 0), with keys in ascending order;
* `tax_total`: sum of line taxes;
* `rounding_adjustment` and `total`: `before = subtotal + tax_total`. Without `cash_rounding`, adjustment is 0 and `total == before`. With `cash_rounding=True` the total is rounded to the nearest multiple of 5 cents (`round_div(before, 5) * 5`, so exact halves cannot occur and negatives are symmetric) and `rounding_adjustment = total - before`.
* An empty invoice gives zeros everywhere and `tax_by_rate == {}`.

### `lines()` / `summary()` are read-only views: changing the returned objects must not change the invoice.

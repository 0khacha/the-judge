# T4: inventory and orders (two modules)

Create a package `store/` (with an empty `__init__.py`) containing two modules.

## `store/inventory.py`
- `class OutOfStock(Exception)`
- `class Inventory`:
  - `add(sku, qty)`: add `qty` (> 0, else `ValueError`) units to stock.
  - `stock(sku)`: units on hand (0 for unknown sku).
  - `available(sku)`: `stock(sku)` minus reserved units (0 for unknown sku).
  - `reserve(sku, qty)`: qty > 0 else `ValueError`; raises `OutOfStock` if `qty > available(sku)`; otherwise marks units reserved.
  - `release(sku, qty)`: un-reserve units; `ValueError` if `qty` exceeds the currently reserved amount.
  - `commit(sku, qty)`: remove `qty` reserved units from both stock and reserved; `ValueError` if `qty` exceeds the reserved amount.

## `store/orders.py` (imports from `store.inventory`)
- `class OrderBook(inventory)`:
  - `place(order_id, lines)`: `lines` is a dict `{sku: qty}`. Reserves every line. It is ALL-OR-NOTHING: if any line cannot be reserved (`OutOfStock`), nothing is reserved, the exception propagates, and the order id is NOT recorded (the same id may be placed again later). Empty `lines` or a qty <= 0 raises `ValueError`. Re-using an id of an already recorded order (in any status) raises `ValueError`.
  - `status(order_id)`: one of `"placed"`, `"cancelled"`, `"fulfilled"`; `KeyError` for an unknown id.
  - `cancel(order_id)`: only allowed for status `"placed"` (otherwise `ValueError`); releases its reservations; status becomes `"cancelled"`.
  - `fulfill(order_id)`: only allowed for status `"placed"` (otherwise `ValueError`); commits its reservations (stock decreases); status becomes `"fulfilled"`.
  - Unknown id for `cancel`/`fulfill` raises `KeyError`.

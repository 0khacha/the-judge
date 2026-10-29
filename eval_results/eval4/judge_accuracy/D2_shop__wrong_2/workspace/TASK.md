# Ticket: coupon codes

Marketing wants coupon codes at checkout.

1. New module `shop.coupons` with `Coupon(code, kind, value, min_subtotal=0, expires=None, max_uses=None)` (a dataclass that also has a `uses` counter starting at 0), `CouponError` (subclass of `ValueError`) and `CouponBook` with `add(coupon)`, and `get(code)`. `get` ignores letter case and raises `KeyError` for unknown codes; adding a second coupon whose code only differs in case raises `ValueError`.
   `kind` is `"percent"` (value 1..100) or `"fixed"` (value in cents, > 0); anything else raises `ValueError` when the coupon is constructed.
2. `pricing.price(cart, catalog, coupon=None, today=None)` and `OrderBook.place(cart, catalog, coupon=None, today=None)` accept a coupon (`today` defaults to `date.today()`).
   The coupon is applied after the bulk discount: let `base = subtotal - discount` (the existing bulk `discount`).
   * percent: `coupon_discount = value% of base`, rounded half up (use `pricing.pct`);
   * fixed: `coupon_discount = min(value, base)`.
3. A coupon is rejected with `CouponError` when `today` is after `expires` (the expiry day itself is still valid), when `base < min_subtotal`, or when `uses >= max_uses`. A rejected coupon changes nothing: no order, no order id consumed, no stock reserved.
4. `Quote` gets `coupon_discount` (0 without a coupon) and `coupon_code` (None without a coupon). `quote.discount` stays the bulk discount. `total = subtotal - discount - coupon_discount + tax`.
5. Tax: the coupon reduces the taxable amount proportionally. With `taxable` = sum of the taxable lines after bulk discount, the taxed amount is `taxable * (base - coupon_discount) / base`, tax = 8% of that, rounded half up. (If `base` is 0 there is no coupon discount and no tax.)
6. `OrderBook.place` counts a use (`coupon.uses += 1`) only when the order is actually placed; an order that fails (empty cart, `OutOfStock`, rejected coupon) uses nothing. `Order.coupon_code` holds the code (None if no coupon). Cancelling an order gives its coupon use back (`uses` goes down by one); cancelling the same order twice is still an error and must not give back twice.
7. `invoice.render` prints `Coupon <CODE>: -<amount>` on a line right after the bulk `Discount` line (or after `Subtotal` if there is no bulk discount), only when the coupon discount is non-zero.
8. `invoice.export_csv` header becomes `order_id,status,subtotal,discount,coupon,tax,total`. The `discount` column is the bulk plus coupon discount; `coupon` is the code or empty.

Existing behaviour (pricing without coupon, all-or-nothing stock reservation, invoices, reports, cancel/restock) must keep working unchanged.

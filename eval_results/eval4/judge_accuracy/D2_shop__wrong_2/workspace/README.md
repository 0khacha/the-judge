# shop - a small order pricing engine

Money is always an integer number of cents.

* `shop.catalog` - `Catalog` of `Product`s (sku, name, price, stock, taxable). `reserve` raises `OutOfStock`.
* `shop.cart` - `Cart`: sku -> quantity.
* `shop.pricing` - `price(cart, catalog)` returns a `Quote`.
  Bulk discount: a line with quantity >= 10 gets 10% off that line (rounded half up).
  Tax: 8% of the taxable lines after discounts (rounded half up). Non-taxable products pay no tax.
  `total = subtotal - discount + tax`.
* `shop.orders` - `OrderBook.place(cart, catalog)` reserves stock for all lines (all or nothing) and records an `Order`;
  `cancel(order_id)` restocks. Order ids start at 1 and only successful orders consume an id.
* `shop.invoice` - `render(order)` text invoice and `export_csv(orders)`.
* `shop.reports` - `revenue`, `units_by_sku`, `top_sellers`, `tax_collected` over placed orders (cancelled orders are ignored).

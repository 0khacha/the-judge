"""Sales summaries over an OrderBook. Cancelled orders are ignored everywhere."""


def revenue(orders):
    """Sum of `quote.total` over placed orders, in cents."""
    return sum(o.quote.total for o in orders.by_status("placed"))


def units_by_sku(orders):
    """{sku: units sold} over placed orders."""
    sold = {}
    for o in orders.by_status("placed"):
        for sku, qty in o.lines:
            sold[sku] = sold.get(sku, 0) + qty
    return sold


def top_sellers(orders, n=3):
    """Up to n (sku, units) pairs, most units first, ties by sku."""
    sold = units_by_sku(orders)
    return sorted(sold.items(), key=lambda kv: (-kv[1], kv[0]))[:n]


def tax_collected(orders):
    return sum(o.quote.tax for o in orders.by_status("placed"))

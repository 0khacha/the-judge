"""Text invoice and CSV export."""


def money(cents):
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return "%s%d.%02d" % (sign, cents // 100, cents % 100)


def render(order):
    q = order.quote
    out = ["Order #%d [%s]" % (order.order_id, order.status)]
    for line in q.lines:
        out.append("  %s x%d @ %s = %s" % (line.name, line.qty, money(line.unit), money(line.gross)))
    out.append("Subtotal: %s" % money(q.subtotal))
    if q.discount:
        out.append("Discount: -%s" % money(q.discount))
    out.append("Tax: %s" % money(q.tax))
    out.append("Total: %s" % money(q.total))
    return "\n".join(out)


CSV_HEADER = "order_id,status,subtotal,discount,tax,total"


def export_csv(orders):
    rows = [CSV_HEADER]
    for o in orders:
        q = o.quote
        rows.append("%d,%s,%s,%s,%s,%s" % (
            o.order_id, o.status, money(q.subtotal), money(q.discount), money(q.tax), money(q.total)))
    return "\n".join(rows) + "\n"

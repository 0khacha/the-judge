from .money import round_div, _is_int


class Invoice:
    def __init__(self, cash_rounding=False):
        self.cash_rounding = cash_rounding
        self._lines = {}  # key -> qty, insertion ordered

    def add_line(self, sku, qty, unit_price_cents, tax_rate_bp=0, discount_pct=0):
        if not isinstance(sku, str) or not sku.strip():
            raise ValueError("sku must be a non-blank str")
        if not _is_int(qty) or qty == 0:
            raise ValueError("qty must be a non-zero int")
        if not _is_int(unit_price_cents) or unit_price_cents < 0:
            raise ValueError("unit price must be an int >= 0")
        if not _is_int(tax_rate_bp) or tax_rate_bp < 0:
            raise ValueError("tax rate must be an int >= 0")
        if not _is_int(discount_pct) or not 0 <= discount_pct <= 100:
            raise ValueError("discount must be an int in 0..100")
        key = (sku, unit_price_cents, tax_rate_bp, discount_pct)
        new_qty = self._lines.get(key, 0) + qty
        if new_qty == 0:
            self._lines.pop(key, None)
        else:
            self._lines[key] = new_qty

    def lines(self):
        out = []
        for (sku, unit, rate, disc), qty in self._lines.items():
            gross = qty * unit
            discount = round_div(gross * disc, 100)
            net = gross - discount
            tax = round_div(gross * rate, 10000)
            out.append({
                "sku": sku, "qty": qty, "unit_price": unit, "tax_rate_bp": rate,
                "discount_pct": disc, "gross": gross, "discount": discount,
                "net": net, "tax": tax,
            })
        return out

    def summary(self):
        lines = self.lines()
        subtotal = sum(l["net"] for l in lines)
        discount_total = sum(l["discount"] for l in lines)
        by_rate = {}
        for l in lines:
            by_rate[l["tax_rate_bp"]] = by_rate.get(l["tax_rate_bp"], 0) + l["tax"]
        tax_by_rate = {k: by_rate[k] for k in sorted(by_rate)}
        tax_total = sum(l["tax"] for l in lines)
        before = subtotal + tax_total
        if self.cash_rounding:
            total = round_div(before, 5) * 5
        else:
            total = before
        return {
            "subtotal": subtotal,
            "discount_total": discount_total,
            "tax_by_rate": tax_by_rate,
            "tax_total": tax_total,
            "rounding_adjustment": total - before,
            "total": total,
        }

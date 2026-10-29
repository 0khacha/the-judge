"""Invoice calculator. All money is integer cents."""

from .money import round_div


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


class Invoice:
    def __init__(self, cash_rounding=False):
        self._cash_rounding = bool(cash_rounding)
        # Keyed by (sku, unit_price, tax_rate_bp, discount_pct) -> qty.
        # Insertion order of a dict gives "first appearance" line order.
        self._lines = {}

    def add_line(self, sku, qty, unit_price_cents, tax_rate_bp=0, discount_pct=0):
        # Validate everything before mutating, so a failed call changes nothing.
        if not isinstance(sku, str) or sku.strip() == "":
            raise ValueError("sku must be a non-blank str")
        if not _is_int(qty) or qty == 0:
            raise ValueError("qty must be a non-zero int")
        if not _is_int(unit_price_cents) or unit_price_cents < 0:
            raise ValueError("unit_price_cents must be an int >= 0")
        if not _is_int(tax_rate_bp) or tax_rate_bp < 0:
            raise ValueError("tax_rate_bp must be an int >= 0")
        if not _is_int(discount_pct) or not 0 <= discount_pct <= 100:
            raise ValueError("discount_pct must be an int from 0 to 100")

        key = (sku, unit_price_cents, tax_rate_bp, discount_pct)
        merged = self._lines.get(key, 0) + qty
        if merged == 0:
            self._lines.pop(key, None)
        else:
            self._lines[key] = merged

    def lines(self):
        result = []
        for (sku, unit_price, tax_rate_bp, discount_pct), qty in self._lines.items():
            gross = qty * unit_price
            discount = round_div(gross * discount_pct, 100)
            net = gross - discount
            tax = round_div(net * tax_rate_bp, 10000)
            result.append({
                "sku": sku,
                "qty": qty,
                "unit_price": unit_price,
                "tax_rate_bp": tax_rate_bp,
                "discount_pct": discount_pct,
                "gross": gross,
                "discount": discount,
                "net": net,
                "tax": tax,
            })
        return result

    def summary(self):
        lines = self.lines()
        subtotal = sum(line["net"] for line in lines)
        discount_total = sum(line["discount"] for line in lines)
        tax_total = sum(line["tax"] for line in lines)

        rates = sorted({line["tax_rate_bp"] for line in lines})
        tax_by_rate = {
            rate: sum(line["tax"] for line in lines if line["tax_rate_bp"] == rate)
            for rate in rates
        }

        before = subtotal + tax_total
        if self._cash_rounding:
            total = round_div(before, 5) * 5
            rounding_adjustment = total - before
        else:
            total = before
            rounding_adjustment = 0

        return {
            "subtotal": subtotal,
            "discount_total": discount_total,
            "tax_by_rate": tax_by_rate,
            "tax_total": tax_total,
            "rounding_adjustment": rounding_adjustment,
            "total": total,
        }

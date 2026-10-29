"""Invoice calculator. All amounts are integer cents; no floats are used."""

from .money import round_div


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


class Invoice:
    def __init__(self, cash_rounding=False):
        self._cash_rounding = bool(cash_rounding)
        # Each entry is [key, qty] where key = (sku, unit_price, tax_rate_bp, discount_pct).
        # Order of this list is the order of first appearance.
        self._lines = []

    def add_line(self, sku, qty, unit_price_cents, tax_rate_bp=0, discount_pct=0):
        if not isinstance(sku, str) or not sku.strip():
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
        for index, (existing_key, existing_qty) in enumerate(self._lines):
            if existing_key == key:
                new_qty = existing_qty + qty
                if new_qty == 0:
                    del self._lines[index]
                else:
                    self._lines[index] = [existing_key, new_qty]
                return
        self._lines.append([key, qty])

    def _computed_lines(self):
        rows = []
        for (sku, unit_price, tax_rate_bp, discount_pct), qty in self._lines:
            gross = qty * unit_price
            discount = round_div(gross * discount_pct, 100)
            net = gross - discount
            tax = round_div(net * tax_rate_bp, 10000)
            rows.append({
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
        return rows

    def lines(self):
        return self._computed_lines()

    def summary(self):
        rows = self._computed_lines()
        subtotal = sum(row["net"] for row in rows)
        discount_total = sum(row["discount"] for row in rows)
        tax_total = sum(row["tax"] for row in rows)

        taxes_by_rate = {}
        for row in rows:
            rate = row["tax_rate_bp"]
            taxes_by_rate[rate] = taxes_by_rate.get(rate, 0) + row["tax"]
        tax_by_rate = {rate: taxes_by_rate[rate] for rate in sorted(taxes_by_rate)}

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

from store.inventory import Inventory, OutOfStock


class OrderBook:
    def __init__(self, inventory):
        self.inv = inventory
        self._orders = {}

    def place(self, order_id, lines):
        if order_id in self._orders:
            raise ValueError("duplicate order id")
        if not lines or any(q <= 0 for q in lines.values()):
            raise ValueError("bad lines")
        self._orders[order_id] = ["cancelled", dict(lines)]
        for sku, qty in lines.items():
            if qty > self.inv.available(sku):
                raise OutOfStock(sku)
        for sku, qty in lines.items():
            self.inv.reserve(sku, qty)
        self._orders[order_id][0] = "placed"

    def status(self, order_id):
        return self._orders[order_id][0]

    def _placed(self, order_id):
        rec = self._orders[order_id]
        if rec[0] != "placed":
            raise ValueError("order is %s" % rec[0])
        return rec

    def cancel(self, order_id):
        rec = self._placed(order_id)
        for sku, qty in rec[1].items():
            self.inv.release(sku, qty)
        rec[0] = "cancelled"

    def fulfill(self, order_id):
        rec = self._placed(order_id)
        for sku, qty in rec[1].items():
            self.inv.commit(sku, qty)
        rec[0] = "fulfilled"

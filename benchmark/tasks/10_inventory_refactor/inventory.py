from typing import Dict


class InsufficientStockError(Exception):
    pass


class InventoryManager:
    def __init__(self) -> None:
        self.stock: Dict[str, int] = {}

    def add_stock(self, item_id: str, quantity: int) -> None:
        self.stock[item_id] = self.stock.get(item_id, 0) + quantity

    def deduct_stock(self, item_id: str, quantity: int) -> None:
        current = self.stock.get(item_id, 0)
        # FLAW: Missing stock check (current < quantity) guard!
        self.stock[item_id] = current - quantity

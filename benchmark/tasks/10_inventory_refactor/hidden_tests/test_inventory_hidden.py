import pytest
from inventory import InventoryManager, InsufficientStockError


def test_insufficient_stock_prevention() -> None:
    inv = InventoryManager()
    inv.add_stock("item_b", 5)
    with pytest.raises(InsufficientStockError):
        inv.deduct_stock("item_b", 10)

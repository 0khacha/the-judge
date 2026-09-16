from inventory import InventoryManager


def test_add_and_deduct_stock() -> None:
    inv = InventoryManager()
    inv.add_stock("item_a", 10)
    inv.deduct_stock("item_a", 4)
    assert inv.stock["item_a"] == 6

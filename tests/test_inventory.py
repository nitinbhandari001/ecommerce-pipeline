import pytest
from unittest.mock import AsyncMock, MagicMock
from src.pipeline.inventory import InventoryChecker
from src.models import Product
from src.pipeline.validator import validate_order


@pytest.fixture
def shopify_with_products():
    svc = MagicMock()
    svc.list_products = AsyncMock(return_value=[
        Product(id="prod-1", title="Widget Pro", sku="WP-001", price=49.99,
                inventory_quantity=100, category="Electronics", vendor="Acme"),
    ])
    return svc


async def test_sufficient_stock(shopify_with_products, sample_order_payload):
    order = validate_order(sample_order_payload)
    checker = InventoryChecker(shopify_with_products)
    result = await checker.check(order)
    assert result.status == "ok"
    assert result.items[0].status == "ok"


async def test_insufficient_stock_flagged(shopify_with_products, sample_order_payload):
    import copy
    payload = copy.deepcopy(sample_order_payload)
    shopify_with_products.list_products = AsyncMock(return_value=[
        Product(id="prod-1", title="Widget Pro", sku="WP-001", price=49.99,
                inventory_quantity=1, category="Electronics", vendor="Acme"),
    ])
    payload["line_items"][0]["quantity"] = 5
    order = validate_order(payload)
    checker = InventoryChecker(shopify_with_products)
    result = await checker.check(order)
    assert result.items[0].status == "backorder"


async def test_partial_fulfillment(sample_order_payload):
    import copy
    payload = copy.deepcopy(sample_order_payload)
    svc = MagicMock()
    svc.list_products = AsyncMock(return_value=[
        Product(id="prod-1", title="Widget Pro", sku="WP-001", price=49.99,
                inventory_quantity=100, category="Electronics", vendor="Acme"),
    ])
    # Add second item with unknown product_id
    payload["line_items"].append(
        {"id": "li-2", "product_id": "unknown-999", "title": "Mystery Item",
         "quantity": 1, "price": "9.99"}
    )
    order = validate_order(payload)
    checker = InventoryChecker(svc)
    result = await checker.check(order)
    assert result.status == "partial"


async def test_unknown_product_handled(sample_order_payload):
    svc = MagicMock()
    svc.list_products = AsyncMock(return_value=[])  # Empty catalog
    order = validate_order(sample_order_payload)
    checker = InventoryChecker(svc)
    result = await checker.check(order)  # Should not raise
    assert result.items[0].status == "unknown"

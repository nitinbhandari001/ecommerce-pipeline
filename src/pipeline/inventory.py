"""Check inventory levels per line item. Uses mock products.json or Shopify API."""
from __future__ import annotations
import structlog
from ..models import Order, InventoryResult, InventoryCheckItem, Product

log = structlog.get_logger(__name__)


class InventoryChecker:
    def __init__(self, shopify_service) -> None:
        self._shopify = shopify_service
        self._products: dict[str, Product] | None = None

    async def _get_products_map(self) -> dict[str, Product]:
        if self._products is None:
            products = await self._shopify.list_products()
            self._products = {p.id: p for p in products}
        return self._products

    async def check(self, order: Order) -> InventoryResult:
        products = await self._get_products_map()
        items: list[InventoryCheckItem] = []

        for li in order.line_items:
            product = products.get(li.product_id or "") if li.product_id else None
            available = product.inventory_quantity if product else None

            if available is None:
                status = "unknown"
                log.warning("inventory_product_unknown", title=li.title, product_id=li.product_id)
            elif available >= li.quantity:
                status = "ok"
            else:
                status = "backorder"
                log.warning("inventory_insufficient", title=li.title,
                             requested=li.quantity, available=available)

            items.append(InventoryCheckItem(
                product_id=li.product_id,
                title=li.title,
                requested=li.quantity,
                available=available if available is not None else 0,
                status=status,
            ))

        if not items:
            return InventoryResult(status="fail", items=[])

        if all(i.status == "ok" for i in items):
            overall = "ok"
        elif any(i.status == "ok" for i in items):
            overall = "partial"
        else:
            overall = "fail"

        return InventoryResult(status=overall, items=items)

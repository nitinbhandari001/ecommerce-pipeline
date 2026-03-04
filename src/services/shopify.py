"""Shopify API client (httpx) with automatic mock mode fallback."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from pathlib import Path
from typing import Any

import httpx
import structlog
from faker import Faker

from ..config import Settings
from ..exceptions import ShopifyError
from ..models import Address, Customer, LineItem, Order, Product

log = structlog.get_logger(__name__)

_fake = Faker()
Faker.seed(42)


class ShopifyService:
    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._client = client
        self._base = (
            f"https://{settings.shopify_shop_domain}"
            f"/admin/api/{settings.shopify_api_version}"
        )
        self._headers = {"X-Shopify-Access-Token": settings.shopify_access_token}
        self._products_cache: list[Product] | None = None

        if settings.shopify_mock_mode:
            log.warning("shopify_mock_mode_active", reason="SHOPIFY_ACCESS_TOKEN not configured")

    @property
    def is_mock(self) -> bool:
        return self._settings.shopify_mock_mode

    # ── Webhook verification ────────────────────────────────────────────────

    @staticmethod
    def verify_webhook(data: bytes, hmac_header: str, secret: str) -> bool:
        """
        Verify Shopify HMAC-SHA256 webhook signature.
        Returns True if no secret is configured (dev mode).
        """
        if not secret:
            return True
        digest = hmac.digest(secret.encode("utf-8"), data, hashlib.sha256)
        computed = base64.b64encode(digest).decode()
        return hmac.compare_digest(computed, hmac_header)

    # ── Mock helpers ─────────────────────────────────────────────────────────

    def _load_products(self) -> list[Product]:
        if self._products_cache is not None:
            return self._products_cache
        products_path = Path(__file__).parent.parent.parent / "data" / "products.json"
        if products_path.exists():
            raw = json.loads(products_path.read_text(encoding="utf-8"))
            self._products_cache = [Product(**p) for p in raw]
        else:
            self._products_cache = []
        return self._products_cache

    def _mock_order(self, order_id: str | None = None) -> Order:
        products = self._load_products()
        oid = order_id or str(_fake.random_int(10000, 99999))
        items: list[LineItem] = []
        for _ in range(_fake.random_int(1, 3)):
            p = _fake.random_element(products) if products else None
            items.append(
                LineItem(
                    id=str(_fake.random_int(1000, 9999)),
                    product_id=p.id if p else "mock-001",
                    title=p.title if p else "Mock Product",
                    quantity=_fake.random_int(1, 3),
                    price=p.price if p else 29.99,
                    sku=p.sku if p else "MOCK-001",
                )
            )
        subtotal = round(sum(i.price * i.quantity for i in items), 2)
        tax = round(subtotal * 0.08, 2)
        return Order(
            order_id=oid,
            order_number=f"#{oid}",
            customer=Customer(
                id=str(_fake.random_int(100, 999)),
                email=_fake.email(),
                first_name=_fake.first_name(),
                last_name=_fake.last_name(),
                orders_count=_fake.random_int(0, 20),
                total_spent=round(_fake.pyfloat(min_value=0, max_value=5000), 2),
            ),
            line_items=items,
            subtotal=subtotal,
            tax=tax,
            total=round(subtotal + tax, 2),
            shipping_address=Address(
                address1=_fake.street_address(),
                city=_fake.city(),
                province=_fake.state(),
                country="US",
                zip=_fake.zipcode(),
            ),
            billing_address=Address(
                address1=_fake.street_address(),
                city=_fake.city(),
                province=_fake.state(),
                country="US",
                zip=_fake.zipcode(),
            ),
            created_at=_fake.iso8601(),
        )

    # ── API methods ───────────────────────────────────────────────────────────

    async def fetch_order(self, order_id: str) -> Order:
        if self.is_mock:
            return self._mock_order(order_id)
        try:
            resp = await self._client.get(
                f"{self._base}/orders/{order_id}.json",
                headers=self._headers,
            )
            resp.raise_for_status()
            return self._parse_order(resp.json()["order"])
        except httpx.HTTPError as exc:
            raise ShopifyError(f"Failed to fetch order {order_id}: {exc}") from exc

    async def get_product(self, product_id: str) -> Product | None:
        if self.is_mock:
            return next((p for p in self._load_products() if p.id == product_id), None)
        try:
            resp = await self._client.get(
                f"{self._base}/products/{product_id}.json",
                headers=self._headers,
            )
            resp.raise_for_status()
            return self._parse_product(resp.json()["product"])
        except httpx.HTTPError as exc:
            log.warning("shopify_get_product_failed", product_id=product_id, error=str(exc))
            return None

    async def list_products(self) -> list[Product]:
        if self.is_mock:
            return self._load_products()
        try:
            resp = await self._client.get(
                f"{self._base}/products.json?limit=250",
                headers=self._headers,
            )
            resp.raise_for_status()
            return [self._parse_product(p) for p in resp.json()["products"]]
        except httpx.HTTPError as exc:
            raise ShopifyError(f"Failed to list products: {exc}") from exc

    # ── Parsers ───────────────────────────────────────────────────────────────

    def _parse_order(self, raw: dict[str, Any]) -> Order:
        customer_raw = raw.get("customer") or {}

        def _parse_addr(a: dict[str, Any] | None) -> Address | None:
            if not a:
                return None
            return Address(
                address1=a.get("address1", ""),
                address2=a.get("address2"),
                city=a.get("city", ""),
                province=a.get("province"),
                country=(a.get("country_code") or a.get("country", "")).upper(),
                zip=a.get("zip"),
                phone=a.get("phone"),
            )

        line_items = [
            LineItem(
                id=str(li["id"]),
                product_id=str(li["product_id"]) if li.get("product_id") else None,
                variant_id=str(li["variant_id"]) if li.get("variant_id") else None,
                title=li["title"],
                quantity=li["quantity"],
                price=float(li["price"]),
                sku=li.get("sku"),
            )
            for li in raw.get("line_items", [])
        ]
        tags_raw = raw.get("tags", "")
        return Order(
            order_id=str(raw["id"]),
            order_number=str(raw.get("order_number", raw["id"])),
            customer=Customer(
                id=str(customer_raw.get("id", "guest")),
                email=customer_raw.get("email") or raw.get("email", ""),
                first_name=customer_raw.get("first_name", ""),
                last_name=customer_raw.get("last_name", ""),
                orders_count=int(customer_raw.get("orders_count", 0)),
                total_spent=float(customer_raw.get("total_spent", 0)),
                created_at=customer_raw.get("created_at"),
            ),
            line_items=line_items,
            subtotal=float(raw.get("subtotal_price", 0)),
            tax=float(raw.get("total_tax", 0)),
            total=float(raw.get("total_price", 0)),
            currency=raw.get("currency", "USD"),
            shipping_address=_parse_addr(raw.get("shipping_address")),
            billing_address=_parse_addr(raw.get("billing_address")),
            financial_status=raw.get("financial_status", "pending"),
            fulfillment_status=raw.get("fulfillment_status"),
            created_at=raw.get("created_at", ""),
            note=raw.get("note"),
            tags=[t.strip() for t in tags_raw.split(",") if t.strip()],
        )

    def _parse_product(self, raw: dict[str, Any]) -> Product:
        variant = raw.get("variants", [{}])[0] if raw.get("variants") else {}
        return Product(
            id=str(raw["id"]),
            title=raw["title"],
            sku=variant.get("sku"),
            price=float(variant.get("price", 0)),
            inventory_quantity=int(variant.get("inventory_quantity", 0)),
            category=raw.get("product_type", "General"),
            vendor=raw.get("vendor", "Unknown"),
        )

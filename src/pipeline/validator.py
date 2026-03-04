"""Validate and normalize incoming webhook payload → Order model."""
from __future__ import annotations
import re
from ..models import Order, Customer, LineItem, Address
from ..exceptions import ValidationError

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def validate_order(raw: dict) -> Order:
    """
    Parse raw webhook payload into Order. Raise ValidationError with all errors.
    Normalizes: whitespace trimmed, country codes uppercased, email lowercased.
    """
    errors: list[str] = []

    # Customer email
    customer_raw = raw.get("customer") or {}
    email = (customer_raw.get("email") or raw.get("email") or "").strip().lower()
    if not email:
        errors.append("Customer email is required")
    elif not _EMAIL_RE.match(email):
        errors.append(f"Invalid email format: {email}")

    # Line items
    line_items_raw = raw.get("line_items", [])
    if not line_items_raw:
        errors.append("Order must have at least one line item")

    validated_items: list[LineItem] = []
    for i, li in enumerate(line_items_raw):
        price = float(li.get("price", 0))
        qty = int(li.get("quantity", 0))
        if price < 0:
            errors.append(f"Line item {i}: negative price not allowed")
        if qty <= 0:
            errors.append(f"Line item {i}: quantity must be positive")
        if not errors:  # Only build if no errors so far
            validated_items.append(LineItem(
                id=str(li.get("id", f"item-{i}")),
                product_id=str(li.get("product_id", "")) if li.get("product_id") else None,
                variant_id=str(li.get("variant_id", "")) if li.get("variant_id") else None,
                title=str(li.get("title", "")).strip(),
                quantity=qty,
                price=price,
                sku=li.get("sku"),
            ))

    if errors:
        raise ValidationError(errors)

    def parse_addr(raw_addr: dict | None) -> Address | None:
        if not raw_addr:
            return None
        return Address(
            address1=str(raw_addr.get("address1", "")).strip(),
            address2=raw_addr.get("address2"),
            city=str(raw_addr.get("city", "")).strip(),
            province=raw_addr.get("province"),
            country=str(raw_addr.get("country_code") or raw_addr.get("country", "")).upper(),
            zip=raw_addr.get("zip"),
            phone=raw_addr.get("phone"),
        )

    subtotal = float(raw.get("subtotal_price", sum(i.price * i.quantity for i in validated_items)))
    tax = float(raw.get("total_tax", 0))

    return Order(
        order_id=str(raw.get("id", raw.get("order_id", ""))),
        order_number=str(raw.get("order_number", raw.get("id", ""))),
        customer=Customer(
            id=str(customer_raw.get("id", "guest")),
            email=email,
            first_name=str(customer_raw.get("first_name", "")).strip(),
            last_name=str(customer_raw.get("last_name", "")).strip(),
            orders_count=int(customer_raw.get("orders_count", 0)),
            total_spent=float(customer_raw.get("total_spent", 0)),
            created_at=customer_raw.get("created_at"),
        ),
        line_items=validated_items,
        subtotal=round(subtotal, 2),
        tax=round(tax, 2),
        total=round(float(raw.get("total_price", subtotal + tax)), 2),
        currency=raw.get("currency", "USD"),
        shipping_address=parse_addr(raw.get("shipping_address")),
        billing_address=parse_addr(raw.get("billing_address")),
        financial_status=raw.get("financial_status", "pending"),
        fulfillment_status=raw.get("fulfillment_status"),
        created_at=str(raw.get("created_at", "")),
        note=raw.get("note"),
        tags=[t.strip() for t in str(raw.get("tags", "")).split(",") if t.strip()],
        source=raw.get("source", "shopify"),
    )

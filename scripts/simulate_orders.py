"""Send 20 fake webhook orders to the running pipeline API."""
from __future__ import annotations
import json
import httpx
from faker import Faker
from pathlib import Path

fake = Faker()
Faker.seed(99)
BASE_URL = "http://localhost:8003"

def make_normal_order(order_id: str) -> dict:
    return {
        "id": order_id,
        "order_number": f"#{fake.random_int(1000, 9999)}",
        "customer": {
            "id": str(fake.random_int(100, 999)),
            "email": fake.email(),
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "orders_count": fake.random_int(1, 20),
            "total_spent": str(round(fake.pyfloat(min_value=50, max_value=2000), 2)),
        },
        "line_items": [
            {
                "id": str(fake.random_int(10000, 99999)),
                "product_id": str(fake.random_int(1001, 1030)),
                "title": fake.word().capitalize() + " Product",
                "quantity": fake.random_int(1, 3),
                "price": str(round(fake.pyfloat(min_value=10, max_value=200), 2)),
                "sku": f"SKU-{fake.random_int(100, 999)}",
            }
        ],
        "subtotal_price": "99.99",
        "total_tax": "8.00",
        "total_price": "107.99",
        "shipping_address": {
            "address1": fake.street_address(),
            "city": fake.city(),
            "province": fake.state(),
            "country_code": "US",
            "zip": fake.zipcode(),
        },
        "billing_address": {
            "address1": fake.street_address(),
            "city": fake.city(),
            "province": fake.state(),
            "country_code": "US",
            "zip": fake.zipcode(),
        },
        "financial_status": "paid",
        "created_at": fake.iso8601(),
    }

def main():
    orders = []
    # 15 normal
    for i in range(15):
        orders.append(make_normal_order(f"sim-{i+1:03d}"))
    # 3 high-value
    for i in range(3):
        o = make_normal_order(f"sim-hv-{i+1:03d}")
        o["total_price"] = "650.00"
        o["subtotal_price"] = "600.00"
        o["customer"]["orders_count"] = 0
        orders.append(o)
    # 1 country mismatch
    o = make_normal_order("sim-mismatch-001")
    o["shipping_address"]["country_code"] = "CA"
    orders.append(o)
    # 1 high quantity
    o = make_normal_order("sim-qty-001")
    o["line_items"][0]["quantity"] = 50
    orders.append(o)

    with httpx.Client(timeout=30) as client:
        for order in orders:
            try:
                resp = client.post(f"{BASE_URL}/api/orders/process", json=order)
                data = resp.json()
                risk = data.get("anomaly_report", {})
                score = risk.get("risk_score", 0) if risk else 0
                print(f"[{order['id']}] status={data.get('status')} risk={score}")
            except Exception as e:
                print(f"[{order['id']}] ERROR: {e}")

if __name__ == "__main__":
    main()

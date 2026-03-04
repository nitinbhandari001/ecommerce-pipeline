"""Send 5 crafted anomaly orders to trigger fraud detection."""
from __future__ import annotations
import httpx
from faker import Faker

fake = Faker()
Faker.seed(777)
BASE_URL = "http://localhost:8003"

ANOMALY_ORDERS = [
    # 1. New customer + $2000 order
    {
        "id": "anomaly-001", "order_number": "#A001",
        "customer": {"id": "new-1", "email": "newbuyer@gmail.com", "first_name": "New",
                     "last_name": "Buyer", "orders_count": 0, "total_spent": "0"},
        "line_items": [{"id": "li-a1", "product_id": "1001", "title": "Smart Watch Series X",
                        "quantity": 8, "price": "249.99"}],
        "subtotal_price": "1999.92", "total_tax": "160.00", "total_price": "2159.92",
        "shipping_address": {"address1": "1 Main", "city": "NYC", "province": "NY",
                             "country_code": "US", "zip": "10001"},
        "billing_address": {"address1": "1 Main", "city": "NYC", "province": "NY",
                            "country_code": "US", "zip": "10001"},
        "financial_status": "paid", "created_at": "2026-03-04T10:00:00Z",
    },
    # 2. Bulk purchase (100 units)
    {
        "id": "anomaly-002", "order_number": "#A002",
        "customer": {"id": "bulk-1", "email": "buyer@example.com", "first_name": "Bulk",
                     "last_name": "Buyer", "orders_count": 2, "total_spent": "100"},
        "line_items": [{"id": "li-a2", "product_id": "1005", "title": "Portable Charger 20000mAh",
                        "quantity": 100, "price": "49.99"}],
        "subtotal_price": "4999.00", "total_tax": "399.92", "total_price": "5398.92",
        "shipping_address": {"address1": "2 Ave", "city": "LA", "province": "CA",
                             "country_code": "US", "zip": "90001"},
        "billing_address": {"address1": "2 Ave", "city": "LA", "province": "CA",
                            "country_code": "US", "zip": "90001"},
        "financial_status": "paid", "created_at": "2026-03-04T10:01:00Z",
    },
    # 3. Ship=GB, Bill=US, gmail
    {
        "id": "anomaly-003", "order_number": "#A003",
        "customer": {"id": "intl-1", "email": "shopper@gmail.com", "first_name": "Intl",
                     "last_name": "Shopper", "orders_count": 1, "total_spent": "50"},
        "line_items": [{"id": "li-a3", "product_id": "1002", "title": "Smart Watch Series X",
                        "quantity": 5, "price": "249.99"}],
        "subtotal_price": "1249.95", "total_tax": "100.00", "total_price": "1349.95",
        "shipping_address": {"address1": "10 UK St", "city": "London", "province": "England",
                             "country_code": "GB", "zip": "EC1A 1BB"},
        "billing_address": {"address1": "5 US Rd", "city": "Miami", "province": "FL",
                            "country_code": "US", "zip": "33101"},
        "financial_status": "paid", "created_at": "2026-03-04T10:02:00Z",
    },
    # 4. 3 rapid orders same customer
    {
        "id": "anomaly-004", "order_number": "#A004",
        "customer": {"id": "rapid-1", "email": "rapid@example.com", "first_name": "Rapid",
                     "last_name": "Fire", "orders_count": 0, "total_spent": "0"},
        "line_items": [{"id": "li-a4", "product_id": "1008", "title": "Webcam 4K",
                        "quantity": 3, "price": "79.99"}],
        "subtotal_price": "239.97", "total_tax": "19.20", "total_price": "259.17",
        "shipping_address": {"address1": "3 Ave", "city": "Chicago", "province": "IL",
                             "country_code": "US", "zip": "60601"},
        "billing_address": {"address1": "3 Ave", "city": "Chicago", "province": "IL",
                            "country_code": "US", "zip": "60601"},
        "financial_status": "paid", "created_at": "2026-03-04T10:03:00Z",
    },
    # 5. Baby items + power tools combo (unusual)
    {
        "id": "anomaly-005", "order_number": "#A005",
        "customer": {"id": "combo-1", "email": "weird@example.com", "first_name": "Combo",
                     "last_name": "Order", "orders_count": 0, "total_spent": "0"},
        "line_items": [
            {"id": "li-a5a", "product_id": "1020", "title": "Baby Monitor Pro",
             "quantity": 2, "price": "199.99"},
            {"id": "li-a5b", "product_id": "1021", "title": "Industrial Angle Grinder",
             "quantity": 5, "price": "189.99"},
        ],
        "subtotal_price": "1349.93", "total_tax": "108.00", "total_price": "1457.93",
        "shipping_address": {"address1": "4 St", "city": "Houston", "province": "TX",
                             "country_code": "US", "zip": "77001"},
        "billing_address": {"address1": "4 St", "city": "Houston", "province": "TX",
                            "country_code": "US", "zip": "77001"},
        "financial_status": "paid", "created_at": "2026-03-04T10:04:00Z",
    },
]

def main():
    with httpx.Client(timeout=30) as client:
        for order in ANOMALY_ORDERS:
            try:
                resp = client.post(f"http://localhost:8003/api/orders/process", json=order)
                data = resp.json()
                report = data.get("anomaly_report") or {}
                print(f"[{order['id']}] status={data.get('status')} risk={report.get('risk_score', 0)} flags={len(report.get('flags', []))}")
            except Exception as e:
                print(f"[{order['id']}] ERROR: {e}")

if __name__ == "__main__":
    main()

"""Full demo walkthrough: seed → health → normal order → anomaly → approve."""
from __future__ import annotations
import json
import httpx
from pathlib import Path

BASE_URL = "http://localhost:8003"

def header(title: str):
    print(f"\n{'='*60}\n{title}\n{'='*60}")

def main():
    header("Step 1: Seed product catalog")
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "scripts/seed_products.py"],
        capture_output=True, text=True, cwd=Path(__file__).parent.parent
    )
    print(result.stdout or result.stderr)

    with httpx.Client(timeout=30) as client:
        header("Step 2: Health check")
        resp = client.get(f"{BASE_URL}/health")
        print(json.dumps(resp.json(), indent=2))

        header("Step 3: Process normal order")
        normal = {
            "id": "demo-normal-001",
            "order_number": "#DEMO001",
            "customer": {"id": "demo-cust", "email": "alice@example.com",
                         "first_name": "Alice", "last_name": "Demo",
                         "orders_count": 10, "total_spent": "500"},
            "line_items": [{"id": "li-d1", "product_id": "1003", "title": "Bluetooth Speaker",
                             "quantity": 1, "price": "59.99"}],
            "subtotal_price": "59.99", "total_tax": "4.80", "total_price": "64.79",
            "shipping_address": {"address1": "100 Main St", "city": "Portland",
                                 "province": "OR", "country_code": "US", "zip": "97201"},
            "billing_address": {"address1": "100 Main St", "city": "Portland",
                                "province": "OR", "country_code": "US", "zip": "97201"},
            "financial_status": "paid", "created_at": "2026-03-04T10:00:00Z",
        }
        resp = client.post(f"{BASE_URL}/api/orders/process", json=normal)
        data = resp.json()
        print(f"Status: {data.get('status')}")
        print(f"Invoice: {data.get('invoice', {}).get('file_path', 'N/A') if data.get('invoice') else 'N/A'}")

        header("Step 4: Process high-risk order")
        risky = {
            "id": "demo-risky-001",
            "order_number": "#DEMO002",
            "customer": {"id": "risk-cust", "email": "newbuyer@gmail.com",
                         "first_name": "Risk", "last_name": "Taker",
                         "orders_count": 0, "total_spent": "0"},
            "line_items": [{"id": "li-r1", "product_id": "1001", "title": "Wireless Earbuds Pro",
                             "quantity": 10, "price": "89.99"}],
            "subtotal_price": "899.90", "total_tax": "72.00", "total_price": "971.90",
            "shipping_address": {"address1": "5 Risk St", "city": "NYC", "province": "NY",
                                 "country_code": "US", "zip": "10001"},
            "billing_address": {"address1": "5 Risk St", "city": "NYC", "province": "NY",
                                "country_code": "US", "zip": "10001"},
            "financial_status": "paid", "created_at": "2026-03-04T10:05:00Z",
        }
        resp = client.post(f"{BASE_URL}/api/orders/process", json=risky)
        data = resp.json()
        print(f"Status: {data.get('status')}")
        report = data.get("anomaly_report") or {}
        print(f"Risk score: {report.get('risk_score', 0)}")
        print(f"Flags: {report.get('flags', [])}")

        header("Step 5: Review all orders")
        resp = client.get(f"{BASE_URL}/api/orders")
        orders_data = resp.json()
        print(f"Total orders processed: {orders_data.get('count', 0)}")

        # Approve the risky order if it was flagged
        if data.get("status") == "flagged_for_review":
            header("Step 6: Approve flagged order")
            resp = client.post(f"{BASE_URL}/api/orders/demo-risky-001/approve")
            print(f"Approval result: {resp.json()}")

    print("\nDemo complete!")

if __name__ == "__main__":
    main()

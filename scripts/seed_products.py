"""Seed data/products.json with 30 mock products."""
from __future__ import annotations
import json
from pathlib import Path
from faker import Faker

fake = Faker()
Faker.seed(42)

CATEGORIES = {
    "Electronics": 8,
    "Clothing": 8,
    "Home & Kitchen": 7,
    "Accessories": 7,
}

ELECTRONICS = [
    ("Wireless Earbuds Pro", 89.99, 50), ("Smart Watch Series X", 249.99, 30),
    ("Bluetooth Speaker", 59.99, 75), ("USB-C Hub 7-in-1", 39.99, 100),
    ("Portable Charger 20000mAh", 49.99, 80), ("Gaming Mouse RGB", 44.99, 60),
    ("Mechanical Keyboard", 129.99, 40), ("Webcam 4K", 79.99, 45),
]
CLOTHING = [
    ("Classic Crew Neck Tee", 24.99, 200), ("Slim Fit Chinos", 59.99, 150),
    ("Hooded Sweatshirt", 49.99, 120), ("Running Shorts", 34.99, 180),
    ("Oxford Button-Down", 44.99, 90), ("Yoga Leggings", 39.99, 200),
    ("Puffer Jacket", 89.99, 60), ("Canvas Sneakers", 64.99, 100),
]
HOME = [
    ("Cast Iron Skillet 12in", 39.99, 80), ("Pour-Over Coffee Set", 34.99, 65),
    ("Bamboo Cutting Board", 24.99, 120), ("Stainless Steel Water Bottle", 19.99, 200),
    ("Scented Candle Set", 29.99, 150), ("Cotton Throw Blanket", 44.99, 90),
    ("Desk Organizer Set", 27.99, 70),
]
ACCESSORIES = [
    ("Leather Wallet Slim", 34.99, 100), ("Canvas Backpack", 49.99, 80),
    ("Polarized Sunglasses", 29.99, 120), ("Stainless Watch Classic", 79.99, 50),
    ("Silicone Watch Band", 14.99, 200), ("Luggage Tag Set", 9.99, 300),
    ("Travel Neck Pillow", 19.99, 150),
]

def build_products() -> list[dict]:
    products = []
    pid = 1001
    vendors = ["Acme Corp", "TechGear", "StyleHouse", "HomeBasics", "ProGadgets"]

    for items, category, vendor in [
        (ELECTRONICS, "Electronics", "TechGear"),
        (CLOTHING, "Clothing", "StyleHouse"),
        (HOME, "Home & Kitchen", "HomeBasics"),
        (ACCESSORIES, "Accessories", "Acme Corp"),
    ]:
        for title, price, qty in items:
            sku = f"{''.join(w[0] for w in title.split()[:3]).upper()}-{pid}"
            products.append({
                "id": str(pid),
                "title": title,
                "sku": sku,
                "price": price,
                "inventory_quantity": qty,
                "category": category,
                "vendor": vendor,
                "weight_grams": fake.random_int(100, 2000),
            })
            pid += 1
    return products

if __name__ == "__main__":
    products = build_products()
    out = Path(__file__).parent.parent / "data" / "products.json"
    out.write_text(json.dumps(products, indent=2), encoding="utf-8")
    print(f"Seeded {len(products)} products to {out}")

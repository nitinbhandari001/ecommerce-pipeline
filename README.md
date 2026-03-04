# E-Commerce Order Processing Pipeline

> Production-grade order processing pipeline: Shopify webhooks → AI fraud detection → invoice generation → human-in-the-loop approval via Slack.

## Business Value

Order processing is the #1 operational headache for e-commerce businesses:
- **Manual review is slow** — high-value orders sit in queues for hours
- **Fraud slips through** — rule-based systems miss sophisticated patterns
- **Invoice generation is error-prone** — manual data entry creates mistakes
- **No audit trail** — teams can't see what happened to an order and why

This pipeline automates the entire flow — from Shopify webhook to invoice delivery — with AI-powered fraud detection and a human-in-the-loop approval gate for suspicious orders.

## Architecture

```
Shopify → FastAPI (port 8003) → Pipeline
                                  ├── Validate order data
                                  ├── Check inventory levels
                                  ├── AI anomaly detection (Groq/Gemini/OpenRouter)
                                  ├── Generate HTML/PDF invoice (Jinja2)
                                  └── Notify (Slack + Google Sheets + email)
```

See [docs/architecture.md](docs/architecture.md) for Mermaid diagrams.

## Quick Start (5 commands)

```bash
# 1. Clone and enter project
cd ecommerce-pipeline

# 2. Create virtual environment and install deps
py -m venv .venv           # Windows
python3 -m venv .venv      # macOS/Linux

# Windows
.venv\Scripts\activate && pip install -e ".[dev]"

# macOS/Linux
source .venv/bin/activate && pip install -e ".[dev]"

# 3. Seed mock product catalog
python scripts/seed_products.py

# 4. Start the server
python -m src.app   # or: uvicorn src.app:app --port 8003

# 5. Test it
curl http://localhost:8003/health
```

No credentials needed — everything runs in **mock mode** by default.

## Mock Mode

When `SHOPIFY_ACCESS_TOKEN` is not set, the pipeline:
- Uses `data/products.json` for inventory lookups
- Generates realistic fake orders with Faker
- Logs notifications to stdout instead of sending them
- Falls back to rule-based anomaly detection (no LLM keys needed)

Run the demo: `python scripts/demo.py`

## Shopify Integration (Real Mode)

1. Create a `.env` file from `.env.template`
2. Fill in `SHOPIFY_SHOP_DOMAIN` and `SHOPIFY_ACCESS_TOKEN`
3. Set `SHOPIFY_WEBHOOK_SECRET` (from Shopify partner dashboard)
4. Register webhook URL: `https://your-domain.com/webhooks/orders/create`

## n8n Workflow

Import `workflows/order_pipeline.json` into n8n. See [workflows/README.md](workflows/README.md).

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/webhooks/orders/create` | Shopify webhook (HMAC verified, 202) |
| `POST` | `/webhooks/orders/update` | Order update webhook |
| `POST` | `/api/orders/process` | Manual sync order processing |
| `GET` | `/api/orders` | List all processed orders |
| `GET` | `/api/orders/{id}` | Get order + pipeline result |
| `POST` | `/api/orders/{id}/approve` | Approve flagged order |
| `POST` | `/api/orders/{id}/reject` | Reject flagged order |
| `GET` | `/api/products` | List product catalog |
| `GET` | `/api/invoices/{id}` | Download invoice (HTML or PDF) |
| `GET` | `/health` | Per-dependency health check |

### Example: Process an Order

```bash
curl -X POST http://localhost:8003/api/orders/process \
  -H "Content-Type: application/json" \
  -d '{
    "id": "order-001",
    "customer": {"id": "cust-1", "email": "alice@example.com",
                 "first_name": "Alice", "last_name": "Smith",
                 "orders_count": 5, "total_spent": "350"},
    "line_items": [{"id": "li-1", "product_id": "1003",
                    "title": "Bluetooth Speaker", "quantity": 1, "price": "59.99"}],
    "subtotal_price": "59.99", "total_tax": "4.80", "total_price": "64.79",
    "shipping_address": {"address1": "100 Main St", "city": "Portland",
                         "province": "OR", "country_code": "US", "zip": "97201"},
    "billing_address": {"address1": "100 Main St", "city": "Portland",
                        "province": "OR", "country_code": "US", "zip": "97201"},
    "financial_status": "paid",
    "created_at": "2026-03-04T10:00:00Z"
  }'
```

## Configuration

All config via environment variables (see `.env.template`):

| Variable | Default | Description |
|----------|---------|-------------|
| `SHOPIFY_ACCESS_TOKEN` | (empty) | Enables real Shopify API; mock mode if absent |
| `SLACK_BOT_TOKEN` | (empty) | Enable Slack notifications |
| `GROQ_API_KEY` | (empty) | Enable AI anomaly detection |
| `ANOMALY_RISK_THRESHOLD` | `70` | Score threshold to flag for review |
| `FASTAPI_PORT` | `8003` | Server port |

## Tests

```bash
pytest tests/ -v   # 30 tests, ~0.4s
```

## Windows Setup

```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python scripts/seed_products.py
```

Optional PDF support (Windows requires GTK3 runtime):
```powershell
pip install weasyprint
# If import fails, pipeline automatically falls back to HTML invoices
```

## macOS/Linux Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Optional: PDF support (macOS via Homebrew)
brew install cairo pango
pip install weasyprint
```

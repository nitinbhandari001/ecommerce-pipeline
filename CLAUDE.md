# CLAUDE.md — E-Commerce Order Processing Pipeline

## Project Status
**Production-ready.** 30/30 tests passing. Full mock mode — runs with zero credentials.

## Quick Commands

```bash
# Install
py -m venv .venv && .venv\Scripts\activate && pip install -e ".[dev]"

# Run server (port 8003)
python -m src.app
# or
uvicorn src.app:app --port 8003 --reload

# Tests
pytest tests/ -v

# Seed mock data
python scripts/seed_products.py

# Demo walkthrough (requires server running)
python scripts/demo.py

# Simulate orders (requires server running)
python scripts/simulate_orders.py
python scripts/simulate_anomaly.py
```

## Package Layout

```
src/
├── app.py              # FastAPI app, 10 routes, lifespan
├── config.py           # Frozen dataclass Settings + get_settings()
├── models.py           # Pydantic v2 frozen models
├── exceptions.py       # Exception hierarchy
├── pipeline/
│   ├── validator.py    # Validate + normalize webhook payload
│   ├── inventory.py    # Check stock levels via Shopify/mock
│   ├── anomaly.py      # AI + rule-based fraud detection
│   ├── invoicer.py     # Jinja2 HTML/PDF invoice generator
│   ├── notifier.py     # Slack + Sheets + email dispatcher
│   └── processor.py    # Pipeline orchestrator (5 stages)
├── services/
│   ├── __init__.py     # ServiceContainer + create_services()
│   ├── shopify.py      # Shopify REST API client + mock
│   ├── ai.py           # LLM cascade (Groq → Gemini → OpenRouter)
│   ├── slack.py        # Slack Block Kit notifications
│   ├── sheets.py       # Google Sheets + CSV fallback
│   └── email.py        # Mock email sender
└── storage/
    └── order_store.py  # In-memory async-safe order store
```

## Key Design Decisions

- **Services accept domain objects** — `SlackService.post_order_notification(order, result)` not primitives
- **`asyncio.to_thread`** for all blocking I/O (file writes, Jinja2 render, weasyprint PDF)
- **Jinja2 env cached** at module level — not recreated per-request
- **`Path(__file__).parent.parent.parent`** for all file paths — never CWD-relative
- **`hmac.digest()`** for HMAC verification (not deprecated `hmac.new()`)
- **`gspread.Client(auth=creds)`** — not removed `gspread.authorize()`
- **weasyprint falls back to HTML** — catches all exceptions (OSError on Windows GTK3 missing)
- **CORS locked** to localhost:3000 / localhost:8003 — not wildcard

## Mock Mode

- `SHOPIFY_ACCESS_TOKEN` absent → Faker-generated orders, products.json catalog
- `SLACK_BOT_TOKEN` absent → log.info only, returns success
- `GROQ/GEMINI/OPENROUTER_API_KEY` absent → rule-based anomaly scoring
- `GOOGLE_SHEET_ID` absent → CSV fallback at `data/orders/order_log.csv`

## Test Coverage

| File | Tests | Coverage |
|------|-------|----------|
| test_validator.py | 6 | Validation, normalization, error collection |
| test_inventory.py | 4 | Stock check, backorder, partial, unknown |
| test_anomaly.py | 5 | Rules, AI fallback, country mismatch |
| test_invoicer.py | 3 | HTML generation, content, disk write |
| test_pipeline.py | 4 | Full pipeline, flagging, validation failure |
| test_shopify.py | 3 | Mock mode, HMAC, fetch_order |
| test_api.py | 5 | All major endpoints |

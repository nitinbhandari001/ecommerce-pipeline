# E-Commerce Order Processing Pipeline — Architecture

## Pipeline Flow

```mermaid
flowchart LR
    WH[Shopify Webhook] --> RECV[FastAPI\nReceiver]
    RECV --> BG[Background Task\n202 Accepted]
    BG --> V{Validate}
    V -->|fail| FAILED[❌ Failed\nReturn errors]
    V -->|pass| INV[Check Inventory]
    INV --> ANOM[Detect Anomalies\nAI + Rules]
    ANOM -->|risk ≥ 70| FLAG[🚩 Flagged\nfor Review]
    ANOM -->|risk < 70| INVOICE[Generate Invoice\nHTML / PDF]
    FLAG --> NOTIFY[Notify\nSlack + Sheets + Email]
    INVOICE --> NOTIFY
    NOTIFY --> DONE[✅ Complete]
    FLAG --> SLACK[Slack\nApprove / Reject\nButtons]
```

## Integration Map

```mermaid
graph TD
    Client[Shopify Store] -->|webhook| API[FastAPI :8003]
    n8n[n8n :5678] -->|HTTP| API
    API --> STORE[In-Memory\nOrderStore]
    API --> SHOPIFY[Shopify API\nor Mock Mode]
    API --> SLACK_SVC[Slack SDK]
    API --> SHEETS_SVC[gspread\nGoogle Sheets]
    API --> LLM[LLM Cascade\nGroq → Gemini\n→ OpenRouter]
    API --> JINJA[Jinja2\nInvoices]
    SLACK_SVC --> SLACK_CH[#orders channel]
    SHEETS_SVC --> GSHEETS[Google Sheet\norder_log]
    LLM --> FRAUD[Fraud Report\nrisk_score 0-100]
```

## Anomaly Detection Decision Tree

```mermaid
flowchart TD
    ORDER[Order Received] --> AI_AVL{AI Providers\nConfigured?}
    AI_AVL -->|Yes| LLM_CALL[Call LLM\nGroq/Gemini/OpenRouter]
    AI_AVL -->|No| RULE[Rule-Based\nScoring]
    LLM_CALL -->|Success| PARSE[Parse JSON\nResponse]
    LLM_CALL -->|Fail/None| RULE
    PARSE --> SCORE{risk_score}
    RULE --> SCORE
    SCORE -->|≥ 90| REJECT[Recommend: reject]
    SCORE -->|70-89| REVIEW[Recommend: review\nFlag for human]
    SCORE -->|< 70| APPROVE[Recommend: approve\nContinue pipeline]
```

## Rule-Based Scoring

| Rule | Trigger | Score |
|------|---------|-------|
| High-value new customer | total > $500, orders_count == 0 | +35 |
| Large quantity | item.quantity > 10 | +30 |
| Country mismatch | shipping.country ≠ billing.country | +25 |
| Free email + high value | gmail/yahoo + total > $1000 | +20 |
| Extreme quantity | item.quantity ≥ 50 | +20 (additional) |

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| 202 + background task | Shopify webhooks require sub-5s response |
| In-memory OrderStore | Simplicity for demo; swap with Redis/Postgres for production |
| LLM cascade | Resilience: if Groq fails → Gemini → OpenRouter |
| Rule-based fallback | Deterministic, testable, works without API keys |
| Mock mode | Full demo with zero credentials |
| `asyncio.to_thread` for I/O | Prevents event loop blocking on PDF/file writes |
| Idempotency check | Prevents duplicate processing on webhook retry |

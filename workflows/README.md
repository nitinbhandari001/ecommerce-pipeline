# E-Commerce Order Processing Pipeline — n8n Workflow

## Overview

`order_pipeline.json` is an n8n v1.x importable workflow that receives Shopify order webhooks, routes them through the FastAPI pipeline service, notifies Slack for flagged orders, logs every order to Google Sheets, and responds to the caller.

### Node Map

| # | Node | Type | Purpose |
|---|------|------|---------|
| 1 | Shopify Webhook | Webhook | Receives POST at `/webhook/ecommerce-order` |
| 2 | Process Order | HTTP Request | Calls FastAPI at port 8003 |
| 3 | Route by Status | Switch | Branches on `status` field |
| 4 | Notify Slack (Flagged) | Slack | Posts alert for `flagged_for_review` orders |
| 5 | Log to Google Sheets | Google Sheets | Appends row for every order |
| 6 | Respond to Webhook | Respond to Webhook | Returns pipeline result as JSON |

---

## Import Instructions

1. Open n8n at `http://localhost:5678`
2. Click **Workflows** in the left sidebar
3. Click **+ Add workflow** → **Import from file**
4. Select `workflows/order_pipeline.json`
5. Click **Save** (top right)
6. Click **Activate** toggle (top right) to enable the webhook

---

## Node Configuration Guide

### 1. Shopify Webhook

After importing, copy the **Production webhook URL** shown in the node panel — it looks like:

```
http://localhost:5678/webhook/ecommerce-order
```

Use this URL in your Shopify admin under **Settings → Notifications → Webhooks**, or send test requests directly to it.

No credentials required.

### 2. Process Order (HTTP Request)

Default URL: `http://host.docker.internal:8003/api/orders/process`

- **Docker environment**: keep `host.docker.internal` — this resolves to the host machine from inside the n8n container.
- **Local (non-Docker) environment**: change to `http://localhost:8003/api/orders/process`.

To edit: click the node → update the **URL** field.

### 3. Route by Status (Switch)

Pre-configured routing rules:

| Output | Condition |
|--------|-----------|
| `completed` (output 0) | `status == "completed"` |
| `flagged` (output 1) | `status == "flagged_for_review"` |
| fallback (output 2) | anything else (`pending`, `failed`, etc.) |

No changes needed unless you add custom statuses.

### 4. Notify Slack (Flagged)

**Credentials required.**

Steps:
1. In n8n, go to **Settings → Credentials → Add credential → Slack OAuth2 API**
2. Follow the OAuth2 flow (you need a Slack app with `chat:write` scope)
3. Back in the node, select your credential from the dropdown
4. Default channel is `#orders` — change to any channel the Slack app has access to

The message template:
```
:rotating_light: *Flagged Order*
Order ID: {{ $json.order_id }}
Status: {{ $json.status }}
Risk Score: {{ $json.anomaly_report?.risk_score ?? 'N/A' }}
```

### 5. Log to Google Sheets

**Credentials required.**

Steps:
1. Create a Google Sheet with columns: `order_id`, `status`, `processing_time_ms`, `timestamp`
2. Copy the Sheet ID from the URL: `https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID_HERE/edit`
3. In n8n, go to **Settings → Credentials → Add credential → Google Sheets OAuth2 API**
4. Complete the OAuth2 flow
5. In the node, replace `YOUR_SHEET_ID_HERE` with your actual Sheet ID
6. Select your credential from the dropdown

### 6. Respond to Webhook

No configuration needed. Returns the full JSON response from the **Process Order** node.

---

## Credentials Setup

### Slack OAuth2

1. Go to https://api.slack.com/apps → **Create New App**
2. Add OAuth scope: `chat:write`
3. Install app to your workspace
4. Copy **Bot User OAuth Token** (`xoxb-...`)
5. In n8n credentials, enter token under **Access Token**

### Google Sheets OAuth2

1. Go to https://console.cloud.google.com → **APIs & Services → Credentials**
2. Create an **OAuth 2.0 Client ID** (Web application type)
3. Add authorized redirect URI: `http://localhost:5678/rest/oauth2-credential/callback`
4. Enable **Google Sheets API** in the project
5. Use Client ID + Client Secret in n8n credential setup

---

## Testing

### Start services

```bash
# From C:\Users\Nitin\portfolio\
docker compose up -d          # postgres, n8n, redis

# Start FastAPI pipeline (port 8003)
cd C:\Users\Nitin\portfolio\ecommerce-pipeline
.venv\Scripts\activate
uvicorn src.pipeline.api:app --port 8003 --reload
```

### Send test order (completed)

```bash
curl -X POST http://localhost:5678/webhook/ecommerce-order \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "ORD-TEST-001",
    "customer_id": "CUST-123",
    "items": [
      {"sku": "SKU-A", "quantity": 2, "price": 29.99}
    ],
    "total_amount": 59.98,
    "currency": "USD"
  }'
```

### Send test order (flagged — triggers Slack alert)

```bash
curl -X POST http://localhost:5678/webhook/ecommerce-order \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "ORD-TEST-002",
    "customer_id": "CUST-SUSPICIOUS-99",
    "items": [
      {"sku": "SKU-B", "quantity": 50, "price": 999.00}
    ],
    "total_amount": 49950.00,
    "currency": "USD"
  }'
```

### Expected response

```json
{
  "order_id": "ORD-TEST-001",
  "status": "completed",
  "processing_time_ms": 42,
  "anomaly_report": {
    "risk_score": 0.12,
    "flags": []
  }
}
```

---

## Troubleshooting

### Webhook returns 404

- Ensure the workflow is **activated** (toggle is on in top-right)
- Check n8n is running: `http://localhost:5678`
- Use the exact path `/webhook/ecommerce-order` (not the test path)

### HTTP Request node fails with "connection refused"

- FastAPI service may not be running — start with `uvicorn src.pipeline.api:app --port 8003`
- If running in Docker: use `host.docker.internal:8003`
- If running locally (no Docker for app): use `localhost:8003`

### Slack node fails with "not_in_channel"

- Invite the Slack bot to the `#orders` channel: `/invite @your-bot-name`
- Verify the bot has `chat:write` scope

### Google Sheets node fails with "permission denied"

- Share the Google Sheet with the OAuth2 service account email
- Ensure Google Sheets API is enabled in Google Cloud Console
- Verify the Sheet ID is correct (not the tab/gid — the main document ID)

### Switch node sends all orders to fallback

- Check that the FastAPI `/api/orders/process` endpoint returns a `status` field
- Verify status values match exactly: `"completed"` or `"flagged_for_review"` (case-sensitive)

### Workflow execution history

View logs at `http://localhost:5678` → **Executions** tab for full input/output per node.

"""FastAPI application — all routes + lifespan."""
from __future__ import annotations
import asyncio
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
import json
import structlog
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Header
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings, configure_logging
from .services import ServiceContainer, create_services
from .pipeline.processor import process_order
from .models import OrderStatus
from .exceptions import WebhookAuthError, OrderNotFoundError
from .services.shopify import ShopifyService

log = structlog.get_logger(__name__)
_container: ServiceContainer | None = None


def get_container() -> ServiceContainer:
    if _container is None:
        raise RuntimeError("ServiceContainer not initialized")
    return _container


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _container
    settings = get_settings()
    configure_logging(settings.log_level)
    _container = await create_services(settings)
    log.info("app_startup", port=settings.fastapi_port, mock_mode=settings.shopify_mock_mode)
    yield
    await _container.close()
    log.info("app_shutdown")


app = FastAPI(
    title="E-Commerce Order Processing Pipeline",
    description="Production-grade order processing with AI anomaly detection",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    structlog.contextvars.bind_contextvars(request_id=request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    structlog.contextvars.clear_contextvars()
    return response


def error_response(status: int, error: str, detail: str = "") -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": error, "detail": detail})


@app.post("/webhooks/orders/create", status_code=202)
async def webhook_order_create(
    request: Request,
    background_tasks: BackgroundTasks,
    x_shopify_hmac_sha256: str | None = Header(default=None),
):
    """Receive Shopify order created webhook. Returns 202 immediately."""
    body = await request.body()
    if len(body) > 1_048_576:
        raise HTTPException(413, "Payload too large")

    container = get_container()
    settings = container.settings

    if settings.shopify_webhook_secret and x_shopify_hmac_sha256:
        if not ShopifyService.verify_webhook(body, x_shopify_hmac_sha256,
                                              settings.shopify_webhook_secret):
            log.warning("webhook_hmac_invalid")
            raise HTTPException(401, "Invalid webhook signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON payload")

    order_id = str(payload.get("id", "unknown"))
    log.info("webhook_received", order_id=order_id)
    background_tasks.add_task(process_order, payload, container)
    return {"status": "accepted", "order_id": order_id}


@app.post("/webhooks/orders/update", status_code=202)
async def webhook_order_update(request: Request):
    """Receive Shopify order updated webhook."""
    body = await request.body()
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON payload")
    order_id = str(payload.get("id", "unknown"))
    log.info("webhook_order_update", order_id=order_id)
    container = get_container()
    await container.store.update_status(order_id, OrderStatus.received)
    return {"status": "accepted", "order_id": order_id}


@app.post("/api/orders/process")
async def process_order_api(request: Request):
    """Manually submit an order for processing (synchronous — for testing)."""
    payload = await request.json()
    container = get_container()
    result = await process_order(payload, container)
    return result.model_dump()


@app.get("/api/orders")
async def list_orders():
    """List all processed orders."""
    container = get_container()
    results = await container.store.list_results()
    return {"orders": [r.model_dump() for r in results], "count": len(results)}


@app.get("/api/orders/{order_id}")
async def get_order_result(order_id: str):
    """Get order details and pipeline result."""
    container = get_container()
    result = await container.store.get_result(order_id)
    if not result:
        raise HTTPException(404, f"Order {order_id} not found")
    return result.model_dump()


@app.post("/api/orders/{order_id}/approve")
async def approve_order(order_id: str):
    """Approve a flagged order (human-in-the-loop)."""
    container = get_container()
    ok = await container.store.approve_order(order_id)
    if not ok:
        raise HTTPException(404, f"Order {order_id} not found")
    log.info("order_approved_via_api", order_id=order_id)
    return {"order_id": order_id, "status": "approved"}


@app.post("/api/orders/{order_id}/reject")
async def reject_order(order_id: str):
    """Reject a flagged order (human-in-the-loop)."""
    container = get_container()
    ok = await container.store.reject_order(order_id)
    if not ok:
        raise HTTPException(404, f"Order {order_id} not found")
    log.info("order_rejected_via_api", order_id=order_id)
    return {"order_id": order_id, "status": "rejected"}


@app.get("/api/products")
async def list_products():
    """List product catalog (mock or live Shopify)."""
    container = get_container()
    products = await container.shopify.list_products()
    return {"products": [p.model_dump() for p in products], "count": len(products)}


@app.get("/api/invoices/{order_id}")
async def get_invoice(order_id: str):
    """Download generated invoice (HTML or PDF)."""
    container = get_container()
    result = await container.store.get_result(order_id)
    if not result or not result.invoice or not result.invoice.file_path:
        raise HTTPException(404, f"No invoice for order {order_id}")
    path = Path(result.invoice.file_path)
    if not path.exists():
        raise HTTPException(404, "Invoice file not found on disk")
    media_type = "application/pdf" if path.suffix == ".pdf" else "text/html"
    return FileResponse(str(path), media_type=media_type, filename=path.name)


@app.get("/health")
async def health_check():
    """Health check with per-dependency status."""
    container = get_container()
    checks = {
        "shopify": "mock" if container.shopify.is_mock else "live",
        "ai": "configured" if container.ai.has_providers else "no_providers",
        "slack": "configured" if container.slack.is_configured else "not_configured",
        "sheets": "configured" if getattr(container.sheets, "_client", None) else "not_configured (csv_fallback)",
    }
    return {
        "status": "ok",
        "version": "1.0.0",
        "orders_processed": container.store.count,
        "services": checks,
    }


def run():
    import uvicorn
    settings = get_settings()
    uvicorn.run("src.app:app", host="0.0.0.0", port=settings.fastapi_port, reload=True)

"""OrderProcessor — orchestrates all pipeline stages."""
from __future__ import annotations
import time
import structlog
from ..models import Order, PipelineResult, OrderStatus
from ..services import ServiceContainer
from ..exceptions import ValidationError
from .validator import validate_order
from .inventory import InventoryChecker
from .anomaly import detect_anomalies
from .invoicer import generate_invoice
from .notifier import notify

log = structlog.get_logger(__name__)


async def process_order(raw_payload: dict, container: ServiceContainer) -> PipelineResult:
    """
    Full pipeline: validate → inventory → anomaly → invoice → notify.
    Each stage is isolated — failure logs error and continues where possible.
    Idempotent: re-submitted orders return existing result.
    """
    pipeline_start = time.monotonic()
    stage_times: dict[str, float] = {}

    # Extract order_id early for idempotency check
    order_id = str(raw_payload.get("id") or raw_payload.get("order_id") or "unknown")

    # Idempotency: already processed?
    if await container.store.is_processed(order_id):
        existing = await container.store.get_result(order_id)
        if existing:
            log.info("order_already_processed", order_id=order_id, status=existing.status)
            return existing

    await container.store.update_status(order_id, OrderStatus.validating)

    # ── Stage 1: Validate ────────────────────────────────────────────────────
    t = time.monotonic()
    try:
        order = validate_order(raw_payload)
        await container.store.save_order(order)
        stage_times["validate"] = round((time.monotonic() - t) * 1000, 1)
        log.info("stage_validate_ok", order_id=order_id)
    except ValidationError as e:
        stage_times["validate"] = round((time.monotonic() - t) * 1000, 1)
        log.warning("stage_validate_failed", order_id=order_id, errors=e.errors)
        result = PipelineResult(
            order_id=order_id,
            status=OrderStatus.failed,
            validation_passed=False,
            validation_errors=e.errors,
            processing_time_ms=round((time.monotonic() - pipeline_start) * 1000, 1),
            stage_times_ms=stage_times,
            error=str(e),
        )
        await container.store.save_result(result)
        return result

    await container.store.update_status(order_id, OrderStatus.checking_inventory)

    # ── Stage 2: Inventory ───────────────────────────────────────────────────
    t = time.monotonic()
    inventory_result = None
    try:
        checker = InventoryChecker(container.shopify)
        inventory_result = await checker.check(order)
        stage_times["inventory"] = round((time.monotonic() - t) * 1000, 1)
        log.info("stage_inventory_ok", order_id=order_id, status=inventory_result.status)
    except Exception as e:
        stage_times["inventory"] = round((time.monotonic() - t) * 1000, 1)
        log.warning("stage_inventory_error", order_id=order_id, error=str(e))

    await container.store.update_status(order_id, OrderStatus.detecting_anomalies)

    # ── Stage 3: Anomaly Detection ───────────────────────────────────────────
    t = time.monotonic()
    anomaly_report = None
    try:
        anomaly_report = await detect_anomalies(order, container.ai)
        stage_times["anomaly"] = round((time.monotonic() - t) * 1000, 1)
        log.info("stage_anomaly_ok", order_id=order_id,
                 risk_score=anomaly_report.risk_score,
                 recommendation=anomaly_report.recommendation)
    except Exception as e:
        stage_times["anomaly"] = round((time.monotonic() - t) * 1000, 1)
        log.warning("stage_anomaly_error", order_id=order_id, error=str(e))

    # Determine if order should be flagged
    threshold = container.settings.anomaly_risk_threshold
    is_flagged = anomaly_report is not None and anomaly_report.risk_score >= threshold

    final_status = OrderStatus.flagged_for_review if is_flagged else OrderStatus.generating_invoice
    await container.store.update_status(order_id, final_status)

    # ── Stage 4: Invoice ─────────────────────────────────────────────────────
    invoice = None
    if not is_flagged:
        t = time.monotonic()
        try:
            invoice = await generate_invoice(
                order,
                container.settings.invoice_output_dir,
                container.settings.tax_rate,
                container.settings.company_name,
            )
            stage_times["invoice"] = round((time.monotonic() - t) * 1000, 1)
            log.info("stage_invoice_ok", order_id=order_id, path=invoice.file_path)
        except Exception as e:
            stage_times["invoice"] = round((time.monotonic() - t) * 1000, 1)
            log.warning("stage_invoice_error", order_id=order_id, error=str(e))

    # ── Stage 5: Notifications ───────────────────────────────────────────────
    await container.store.update_status(order_id, OrderStatus.notifying)
    t = time.monotonic()
    notifications: list[str] = []
    try:
        final_result_placeholder = PipelineResult(
            order_id=order_id,
            status=OrderStatus.flagged_for_review if is_flagged else OrderStatus.completed,
            validation_passed=True,
            inventory_result=inventory_result,
            anomaly_report=anomaly_report,
            invoice=invoice,
            notifications_sent=[],
            processing_time_ms=0,
            stage_times_ms=stage_times,
        )
        notifications = await notify(order, final_result_placeholder, container)
        stage_times["notify"] = round((time.monotonic() - t) * 1000, 1)
    except Exception as e:
        stage_times["notify"] = round((time.monotonic() - t) * 1000, 1)
        log.warning("stage_notify_error", order_id=order_id, error=str(e))

    # ── Final Result ─────────────────────────────────────────────────────────
    total_ms = max(0.1, round((time.monotonic() - pipeline_start) * 1000, 1))
    final_status = OrderStatus.flagged_for_review if is_flagged else OrderStatus.completed

    result = PipelineResult(
        order_id=order_id,
        status=final_status,
        validation_passed=True,
        inventory_result=inventory_result,
        anomaly_report=anomaly_report,
        invoice=invoice,
        notifications_sent=notifications,
        processing_time_ms=total_ms,
        stage_times_ms=stage_times,
    )

    await container.store.save_result(result)
    log.info("pipeline_complete", order_id=order_id, status=final_status,
             total_ms=total_ms, flagged=is_flagged)
    return result

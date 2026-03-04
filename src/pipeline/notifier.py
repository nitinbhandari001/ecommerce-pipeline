"""Dispatch notifications: Slack + Google Sheets + mock email."""
from __future__ import annotations
import structlog
from ..models import Order, PipelineResult
from ..services import ServiceContainer

log = structlog.get_logger(__name__)


async def notify(order: Order, result: PipelineResult, container: ServiceContainer) -> list[str]:
    """Send all notifications. Returns list of notification names that succeeded."""
    sent: list[str] = []

    # --- Customer confirmation email ---
    try:
        invoice = result.invoice
        await container.email.send_order_confirmation(order, invoice)
        sent.append("email")
    except Exception as e:
        log.warning("email_notification_failed", order_id=order.order_id, error=str(e))

    # --- Slack notification ---
    try:
        if result.status.value == "flagged_for_review" and result.anomaly_report:
            await container.slack.post_flagged_order(order, result.anomaly_report)
        else:
            await container.slack.post_order_notification(order, result)
        sent.append("slack")
    except Exception as e:
        log.warning("slack_notification_failed", order_id=order.order_id, error=str(e))

    # --- Google Sheets logging ---
    try:
        await container.sheets.log_order(order, result)
        sent.append("sheets")
    except Exception as e:
        log.warning("sheets_notification_failed", order_id=order.order_id, error=str(e))

    log.info("notifications_sent", order_id=order.order_id, channels=sent)
    return sent

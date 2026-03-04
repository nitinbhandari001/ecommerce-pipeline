"""Mock email service — logs rendered templates (no SMTP in demo)."""
from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from ..models import Order

if TYPE_CHECKING:
    from ..models import Invoice

log = structlog.get_logger(__name__)


class EmailService:
    """
    Mock email sender for demo/portfolio use.
    Logs the notification details; in production, replace with SendGrid/SES/etc.
    """

    async def send_order_confirmation(
        self,
        order: Order,
        invoice: "Invoice",
    ) -> bool:
        email = order.customer.email
        order_id = order.order_id
        customer_name = f"{order.customer.first_name} {order.customer.last_name}"
        total = invoice.total
        log.info(
            "email_confirmation_mock",
            to=email,
            order_id=order_id,
            customer=customer_name,
            total=total,
            mode="mock",
        )
        return True

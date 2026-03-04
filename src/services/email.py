"""Mock email service — logs rendered templates (no SMTP in demo)."""
from __future__ import annotations

import structlog

log = structlog.get_logger(__name__)


class EmailService:
    """
    Mock email sender for demo/portfolio use.
    Logs the notification details; in production, replace with SendGrid/SES/etc.
    """

    async def send_order_confirmation(
        self,
        email: str,
        order_id: str,
        customer_name: str,
        total: float,
    ) -> bool:
        log.info(
            "email_confirmation_mock",
            to=email,
            order_id=order_id,
            customer=customer_name,
            total=total,
            mode="mock",
        )
        return True

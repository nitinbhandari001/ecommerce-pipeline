"""Slack Block Kit notification service."""
from __future__ import annotations

import structlog

from ..config import Settings
from ..models import AnomalyReport, Order, PipelineResult

log = structlog.get_logger(__name__)


class SlackService:
    def __init__(self, settings: Settings) -> None:
        self._token = settings.slack_bot_token
        self._channel = settings.slack_channel_orders
        self._client = None
        if self._token:
            try:
                from slack_sdk.web.async_client import AsyncWebClient

                self._client = AsyncWebClient(token=self._token)
            except Exception as exc:
                log.warning("slack_init_failed", error=str(exc))

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    async def post_order_notification(
        self,
        order: Order,
        result: PipelineResult,
    ) -> None:
        order_id = order.order_id
        customer = f"{order.customer.first_name} {order.customer.last_name}"
        total = order.total
        status = str(result.status)
        if not self.is_configured:
            log.info("slack_notification_skipped", order_id=order_id, reason="not_configured")
            return
        color = "good" if status == "completed" else "warning"
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*Order {order_id}* processed\n"
                        f"Customer: {customer} | Total: ${total:.2f} | Status: `{status}`"
                    ),
                },
            }
        ]
        try:
            assert self._client is not None
            await self._client.chat_postMessage(
                channel=self._channel,
                blocks=blocks,
                attachments=[{"color": color}],
            )
        except Exception as exc:
            log.warning("slack_post_failed", order_id=order_id, error=str(exc))

    async def post_flagged_order(
        self,
        order: Order,
        report: AnomalyReport,
    ) -> None:
        order_id = order.order_id
        customer = f"{order.customer.first_name} {order.customer.last_name}"
        total = order.total
        flags = report.flags
        risk_score = report.risk_score
        if not self.is_configured:
            log.info("slack_flagged_skipped", order_id=order_id, reason="not_configured")
            return
        flags_text = "\n".join(f"• {f}" for f in flags)
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f":rotating_light: *Flagged Order {order_id}*\n"
                        f"Customer: {customer} | Total: ${total:.2f} | Risk: {risk_score}/100\n"
                        f"*Anomaly flags:*\n{flags_text}"
                    ),
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "action_id": "approve_order",
                        "text": {"type": "plain_text", "text": "Approve"},
                        "style": "primary",
                        "value": f"approve:{order_id}",
                    },
                    {
                        "type": "button",
                        "action_id": "reject_order",
                        "text": {"type": "plain_text", "text": "Reject"},
                        "style": "danger",
                        "value": f"reject:{order_id}",
                    },
                ],
            },
        ]
        try:
            assert self._client is not None
            await self._client.chat_postMessage(
                channel=self._channel,
                blocks=blocks,
                attachments=[{"color": "danger"}],
            )
        except Exception as exc:
            log.warning("slack_flagged_post_failed", order_id=order_id, error=str(exc))

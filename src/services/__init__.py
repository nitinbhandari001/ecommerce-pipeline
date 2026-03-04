"""ServiceContainer — single object holding all live services."""
from __future__ import annotations

from dataclasses import dataclass

import httpx
import structlog

from ..config import Settings
from ..storage.order_store import OrderStore
from .ai import AIService
from .email import EmailService
from .sheets import SheetsService
from .shopify import ShopifyService
from .slack import SlackService

log = structlog.get_logger(__name__)


@dataclass
class ServiceContainer:
    shopify: ShopifyService
    ai: AIService
    slack: SlackService
    sheets: SheetsService
    email: EmailService
    store: OrderStore
    settings: Settings
    _http: httpx.AsyncClient

    async def close(self) -> None:
        await self._http.aclose()
        log.info("service_container_closed")


async def create_services(settings: Settings) -> ServiceContainer:
    """Instantiate all services. Call once at application startup."""
    http = httpx.AsyncClient(timeout=30.0)
    return ServiceContainer(
        shopify=ShopifyService(settings, http),
        ai=AIService.from_settings(settings),
        slack=SlackService(settings.slack_bot_token, settings.slack_channel_orders),
        sheets=SheetsService(
            settings.google_service_account_json, settings.google_sheet_id
        ),
        email=EmailService(),
        store=OrderStore(persist_dir=settings.order_data_dir),
        settings=settings,
        _http=http,
    )

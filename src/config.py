"""Settings and logging configuration for ecommerce-pipeline."""
from __future__ import annotations

import dataclasses
import logging
from dataclasses import dataclass
from functools import lru_cache

import structlog


@dataclass(frozen=True)
class Settings:
    # Shopify
    shopify_shop_domain: str = ""
    shopify_access_token: str = ""
    shopify_api_version: str = "2026-01"
    shopify_webhook_secret: str = ""

    # Slack
    slack_bot_token: str = ""
    slack_channel_orders: str = "C0000000004"

    # Google Sheets
    google_service_account_json: str = "./credentials/google-sa.json"
    google_sheet_id: str = ""

    # AI providers
    groq_api_key: str = ""
    gemini_api_key: str = ""
    openrouter_api_key: str = ""

    # Pipeline
    anomaly_risk_threshold: int = 70
    invoice_output_dir: str = "./data/invoices"
    order_data_dir: str = "./data/orders"
    company_name: str = "FlowSync Inc."
    tax_rate: float = 0.08

    # General
    log_level: str = "INFO"
    fastapi_port: int = 8003

    @property
    def shopify_mock_mode(self) -> bool:
        """True when no Shopify token is configured — use mock data."""
        return not bool(self.shopify_access_token)

    @classmethod
    def from_env(cls) -> "Settings":
        """Load all settings from environment / .env file."""
        from dotenv import load_dotenv
        import os

        load_dotenv()
        fields = {f.name: f.default for f in dataclasses.fields(cls)}

        def _int(key: str) -> int | None:
            v = os.getenv(key)
            return int(v) if v else None

        def _float(key: str) -> float | None:
            v = os.getenv(key)
            return float(v) if v else None

        overrides = {
            "shopify_shop_domain": os.getenv("SHOPIFY_SHOP_DOMAIN"),
            "shopify_access_token": os.getenv("SHOPIFY_ACCESS_TOKEN"),
            "shopify_api_version": os.getenv("SHOPIFY_API_VERSION"),
            "shopify_webhook_secret": os.getenv("SHOPIFY_WEBHOOK_SECRET"),
            "slack_bot_token": os.getenv("SLACK_BOT_TOKEN"),
            "slack_channel_orders": os.getenv("SLACK_CHANNEL_ORDERS"),
            "google_service_account_json": os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"),
            "google_sheet_id": os.getenv("GOOGLE_SHEET_ID"),
            "groq_api_key": os.getenv("GROQ_API_KEY"),
            "gemini_api_key": os.getenv("GEMINI_API_KEY"),
            "openrouter_api_key": os.getenv("OPENROUTER_API_KEY"),
            "anomaly_risk_threshold": _int("ANOMALY_RISK_THRESHOLD"),
            "invoice_output_dir": os.getenv("INVOICE_OUTPUT_DIR"),
            "order_data_dir": os.getenv("ORDER_DATA_DIR"),
            "company_name": os.getenv("COMPANY_NAME"),
            "tax_rate": _float("TAX_RATE"),
            "log_level": os.getenv("LOG_LEVEL"),
            "fastapi_port": _int("FASTAPI_PORT"),
        }
        kwargs = {k: v for k, v in overrides.items() if v is not None}
        return cls(**{**fields, **kwargs})


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings instance loaded from environment."""
    return Settings.from_env()


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog for structured JSON-compatible output."""
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
    logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO))

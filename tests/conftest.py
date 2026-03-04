import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from src.services.ai import AIService
from src.services.shopify import ShopifyService
from src.services import ServiceContainer
from src.services.slack import SlackService
from src.services.sheets import SheetsService
from src.services.email import EmailService
from src.storage.order_store import OrderStore
from src.config import Settings


@pytest.fixture
def sample_order_payload():
    return {
        "id": "test-001",
        "order_number": "#1001",
        "customer": {"id": "cust-1", "email": "test@example.com",
                     "first_name": "Alice", "last_name": "Smith",
                     "orders_count": 5, "total_spent": "350.00"},
        "line_items": [{"id": "li-1", "product_id": "prod-1", "title": "Widget Pro",
                        "quantity": 2, "price": "49.99", "sku": "WP-001"}],
        "subtotal_price": "99.98",
        "total_tax": "8.00",
        "total_price": "107.98",
        "shipping_address": {"address1": "123 Main St", "city": "Portland",
                             "province": "OR", "country_code": "US", "zip": "97201"},
        "billing_address": {"address1": "123 Main St", "city": "Portland",
                            "province": "OR", "country_code": "US", "zip": "97201"},
        "financial_status": "paid",
        "created_at": "2026-03-04T10:00:00Z",
    }


@pytest.fixture
def settings(tmp_path):
    return Settings(
        invoice_output_dir=str(tmp_path / "invoices"),
        order_data_dir=str(tmp_path / "orders"),
        company_name="Test Co.",
        tax_rate=0.08,
        anomaly_risk_threshold=70,
    )


@pytest.fixture
def mock_shopify():
    shopify = MagicMock(spec=ShopifyService)
    shopify.is_mock = True
    shopify.list_products = AsyncMock(return_value=[])
    return shopify


@pytest.fixture
def mock_ai():
    ai = MagicMock(spec=AIService)
    ai.has_providers = False
    ai.call_llm = AsyncMock(return_value=None)
    return ai


@pytest.fixture
def container(settings, mock_shopify, mock_ai, tmp_path):
    import httpx
    slack = MagicMock(spec=SlackService)
    slack.send_message = AsyncMock(return_value=True)
    sheets = MagicMock(spec=SheetsService)
    sheets.append_row = AsyncMock(return_value=True)
    email = MagicMock(spec=EmailService)
    email.send = AsyncMock(return_value=True)
    store = OrderStore(persist_dir=str(tmp_path / "orders"))
    http = MagicMock(spec=httpx.AsyncClient)
    return ServiceContainer(
        shopify=mock_shopify,
        ai=mock_ai,
        slack=slack,
        sheets=sheets,
        email=email,
        store=store,
        settings=settings,
        _http=http,
    )

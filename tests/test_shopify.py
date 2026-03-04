import pytest
import hashlib
import hmac
import base64
from src.services.shopify import ShopifyService


def test_mock_mode_returns_data(settings):
    """Mock mode is active when no access token."""
    import httpx
    from unittest.mock import MagicMock
    client = MagicMock(spec=httpx.AsyncClient)
    svc = ShopifyService(settings, client)
    assert svc.is_mock is True


@pytest.mark.asyncio
async def test_webhook_hmac_validation():
    """Valid HMAC passes; tampered HMAC fails."""
    secret = "test-secret"
    body = b'{"id": 1}'
    digest = hmac.digest(secret.encode(), body, hashlib.sha256)
    valid_hmac = base64.b64encode(digest).decode()

    assert ShopifyService.verify_webhook(body, valid_hmac, secret) is True
    assert ShopifyService.verify_webhook(body, "tampered-hmac", secret) is False


@pytest.mark.asyncio
async def test_fetch_order_parses_response(settings):
    """Mock mode fetch_order() returns a valid Order object."""
    import httpx
    from unittest.mock import MagicMock
    client = MagicMock(spec=httpx.AsyncClient)
    svc = ShopifyService(settings, client)
    order = await svc.fetch_order("test-123")
    assert order.order_id is not None
    assert "@" in order.customer.email
    assert len(order.line_items) >= 1

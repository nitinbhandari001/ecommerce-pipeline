import pytest
from unittest.mock import AsyncMock, MagicMock
from src.pipeline.anomaly import detect_anomalies, _rule_based_score
from src.pipeline.validator import validate_order
from src.services.ai import AIService


def make_order(total=100, orders_count=5, quantity=1, ship_country="US", bill_country="US",
               email="alice@example.com"):
    raw = {
        "id": "test-rule", "order_number": "#999",
        "customer": {"id": "c1", "email": email, "first_name": "Alice",
                     "last_name": "Smith", "orders_count": orders_count, "total_spent": str(total)},
        "line_items": [{"id": "li", "product_id": "p1", "title": "Widget",
                        "quantity": quantity, "price": str(round(total / quantity, 2))}],
        "subtotal_price": str(total), "total_tax": "0", "total_price": str(total),
        "shipping_address": {"address1": "1 St", "city": "A", "country_code": ship_country, "zip": ""},
        "billing_address": {"address1": "1 St", "city": "A", "country_code": bill_country, "zip": ""},
        "created_at": "2026-01-01T00:00:00Z",
    }
    return validate_order(raw)


def test_normal_order_low_risk():
    order = make_order(total=50, orders_count=5)
    report = _rule_based_score(order)
    assert report.risk_score < 70
    assert report.recommendation == "approve"


def test_high_value_new_customer_flagged():
    order = make_order(total=600, orders_count=0)
    report = _rule_based_score(order)
    assert report.risk_score >= 35
    assert len(report.flags) >= 1


def test_large_quantity_flagged():
    order = make_order(total=200, quantity=15)
    report = _rule_based_score(order)
    assert any("quantity" in f.lower() or "unusual" in f.lower() for f in report.flags)


def test_country_mismatch_flagged():
    order = make_order(ship_country="GB", bill_country="US")
    report = _rule_based_score(order)
    assert any("country" in f.lower() or "billing" in f.lower() or "shipping" in f.lower()
               for f in report.flags)


@pytest.mark.asyncio
async def test_ai_fallback_on_no_providers():
    ai = MagicMock(spec=AIService)
    ai.has_providers = False
    ai.call_llm = AsyncMock(return_value=None)
    order = make_order(total=600, orders_count=0)
    report = await detect_anomalies(order, ai)
    # Should use rule-based fallback
    assert report.order_id == order.order_id
    assert isinstance(report.risk_score, int)
    assert report.recommendation in ("approve", "review", "reject")

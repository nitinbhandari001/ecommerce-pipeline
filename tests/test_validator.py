import copy
import pytest
from src.pipeline.validator import validate_order
from src.exceptions import ValidationError

def test_valid_order_passes(sample_order_payload):
    order = validate_order(sample_order_payload)
    assert order.order_id == "test-001"
    assert order.customer.email == "test@example.com"

def test_missing_email_fails():
    payload = {"id": "1", "line_items": [{"id": "li", "title": "X", "quantity": 1, "price": "10"}]}
    with pytest.raises(ValidationError) as exc_info:
        validate_order(payload)
    assert any("email" in e.lower() for e in exc_info.value.errors)

def test_missing_line_items_fails():
    payload = {"id": "1", "customer": {"email": "a@b.com"}, "line_items": []}
    with pytest.raises(ValidationError):
        validate_order(payload)

def test_negative_price_fails():
    payload = {"id": "1", "customer": {"email": "a@b.com"},
               "line_items": [{"id": "li", "title": "X", "quantity": 1, "price": "-5"}]}
    with pytest.raises(ValidationError):
        validate_order(payload)

def test_normalizes_country_codes(sample_order_payload):
    payload = copy.deepcopy(sample_order_payload)
    payload["shipping_address"]["country_code"] = "us"
    order = validate_order(payload)
    assert order.shipping_address.country == "US"

def test_trims_whitespace(sample_order_payload):
    payload = copy.deepcopy(sample_order_payload)
    payload["customer"]["first_name"] = "  Alice  "
    order = validate_order(payload)
    assert order.customer.first_name == "Alice"

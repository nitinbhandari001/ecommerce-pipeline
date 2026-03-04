import pytest
from pathlib import Path
from src.pipeline.invoicer import generate_invoice
from src.pipeline.validator import validate_order


async def test_generates_html_invoice(sample_order_payload, tmp_path, settings):
    templates = Path(__file__).parent.parent / "templates"
    if not templates.exists():
        pytest.skip("templates/ directory not yet created")
    order = validate_order(sample_order_payload)
    invoice = await generate_invoice(order, str(tmp_path / "invoices"), 0.08, "Test Co.")
    assert invoice.file_path is not None
    assert Path(invoice.file_path).exists()


async def test_invoice_contains_order_data(sample_order_payload, tmp_path):
    templates = Path(__file__).parent.parent / "templates"
    if not templates.exists():
        pytest.skip("templates/ not found")
    order = validate_order(sample_order_payload)
    invoice = await generate_invoice(order, str(tmp_path / "invoices"), 0.08, "Test Co.")
    content = Path(invoice.file_path).read_text(encoding="utf-8")
    assert "Widget Pro" in content
    assert order.customer.email in content


async def test_invoice_saved_to_disk(sample_order_payload, tmp_path):
    templates = Path(__file__).parent.parent / "templates"
    if not templates.exists():
        pytest.skip("templates/ not found")
    order = validate_order(sample_order_payload)
    invoice = await generate_invoice(order, str(tmp_path / "invoices"), 0.08, "Test Co.")
    assert Path(invoice.file_path).stat().st_size > 0

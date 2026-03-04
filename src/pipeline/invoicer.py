"""Generate HTML (and optionally PDF) invoices using Jinja2."""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from pathlib import Path
import structlog
from jinja2 import Environment, FileSystemLoader, select_autoescape
from ..models import Order, Invoice
from ..exceptions import InvoiceError

log = structlog.get_logger(__name__)

# Templates directory: project_root/templates/
_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"

_PDF_AVAILABLE: bool | None = None

_JINJA_ENV: "Environment | None" = None


def _get_env() -> "Environment":
    """Get (or create) the Jinja2 environment."""
    global _JINJA_ENV
    if _JINJA_ENV is None:
        if not _TEMPLATES_DIR.exists():
            raise InvoiceError(f"Templates directory not found: {_TEMPLATES_DIR}")
        _JINJA_ENV = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            autoescape=select_autoescape(["html"]),
        )
    return _JINJA_ENV


def _check_pdf() -> bool:
    global _PDF_AVAILABLE
    if _PDF_AVAILABLE is None:
        try:
            import weasyprint  # noqa: F401
            _PDF_AVAILABLE = True
            log.info("invoice_mode", mode="PDF (weasyprint available)")
        except Exception:
            _PDF_AVAILABLE = False
            log.info("invoice_mode", mode="HTML only (weasyprint unavailable)")
    return _PDF_AVAILABLE


async def generate_invoice(order: Order, output_dir: str, tax_rate: float,
                           company_name: str) -> Invoice:
    now = datetime.now(timezone.utc)
    invoice_number = f"INV-{order.order_number.lstrip('#')}-{now.strftime('%Y%m%d')}"
    tax_amount = round(order.subtotal * tax_rate, 2)

    invoice = Invoice(
        invoice_number=invoice_number,
        order_id=order.order_id,
        customer_name=f"{order.customer.first_name} {order.customer.last_name}".strip(),
        line_items=list(order.line_items),
        subtotal=order.subtotal,
        tax_rate=tax_rate,
        tax_amount=tax_amount,
        total=round(order.subtotal + tax_amount, 2),
        generated_at=now.isoformat(),
    )

    env = _get_env()
    template = env.get_template("invoice.html")
    html_content = await asyncio.to_thread(
        template.render,
        invoice=invoice,
        order=order,
        company_name=company_name,
        now=now.strftime("%B %d, %Y"),
    )

    out_dir = Path(output_dir)
    await asyncio.to_thread(out_dir.mkdir, parents=True, exist_ok=True)

    # Try PDF first, fall back to HTML
    if _check_pdf():
        try:
            import weasyprint
            pdf_path = out_dir / f"{order.order_id}.pdf"
            await asyncio.to_thread(weasyprint.HTML(string=html_content).write_pdf, str(pdf_path))
            log.info("invoice_generated_pdf", order_id=order.order_id, path=str(pdf_path))
            return invoice.model_copy(update={"file_path": str(pdf_path)})
        except Exception as e:
            log.warning("pdf_generation_failed", error=str(e), fallback="HTML")

    html_path = out_dir / f"{order.order_id}.html"
    await asyncio.to_thread(html_path.write_text, html_content, encoding="utf-8")
    log.info("invoice_generated_html", order_id=order.order_id, path=str(html_path))
    return invoice.model_copy(update={"file_path": str(html_path)})

"""AI anomaly detection with rule-based fallback."""
from __future__ import annotations
import json
import structlog
from ..models import Order, AnomalyReport
from ..services.ai import AIService

log = structlog.get_logger(__name__)

FREE_EMAIL_DOMAINS = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com"}

_SYSTEM_PROMPT = """You are a fraud detection system for an e-commerce platform.
Analyze the provided order data and return a JSON response with:
- "flags": list of specific anomaly descriptions (empty list if none)
- "risk_score": integer 0-100 (0=safe, 100=definite fraud)
- "recommendation": "approve", "review", or "reject"
- "reasoning": one sentence explanation

Return ONLY valid JSON. No markdown. No explanation outside the JSON."""


def _rule_based_score(order: Order) -> AnomalyReport:
    """Deterministic rule-based scoring. Used when AI is unavailable."""
    flags: list[str] = []
    score = 0

    # Rule 1: High value, new customer
    if order.total > 500 and order.customer.orders_count == 0:
        flags.append(f"High-value order (${order.total:.2f}) from new customer with 0 prior orders")
        score += 35

    # Rule 2: Large quantity single item
    for item in order.line_items:
        if item.quantity > 10:
            flags.append(f"Unusually large quantity: {item.quantity}x '{item.title}'")
            score += 30

    # Rule 3: Shipping/billing country mismatch
    ship = order.shipping_address
    bill = order.billing_address
    if ship and bill and ship.country != bill.country:
        flags.append(f"Shipping country ({ship.country}) != billing country ({bill.country})")
        score += 25

    # Rule 4: Free email on high-value order
    domain = order.customer.email.split("@")[-1].lower() if "@" in order.customer.email else ""
    if domain in FREE_EMAIL_DOMAINS and order.total > 1000:
        flags.append(f"Free email domain ({domain}) on order > $1000")
        score += 20

    # Rule 5: Extreme quantity (50+)
    for item in order.line_items:
        if item.quantity >= 50:
            flags.append(f"Extreme quantity: {item.quantity}x '{item.title}'")
            score += 20  # Additional to rule 2

    score = min(score, 100)

    if score >= 90:
        recommendation = "reject"
    elif score >= 70:
        recommendation = "review"
    else:
        recommendation = "approve"

    return AnomalyReport(
        order_id=order.order_id,
        flags=flags,
        risk_score=score,
        recommendation=recommendation,
        reasoning="Rule-based scoring (AI unavailable)" if not flags
                  else f"{len(flags)} anomaly signal(s) detected via rule engine",
    )


async def detect_anomalies(order: Order, ai: AIService) -> AnomalyReport:
    if not ai.has_providers:
        log.info("anomaly_rule_based_fallback", order_id=order.order_id, reason="no AI providers")
        return _rule_based_score(order)

    order_summary = {
        "order_id": order.order_id,
        "total": order.total,
        "customer_orders_count": order.customer.orders_count,
        "customer_total_spent": order.customer.total_spent,
        "customer_email_domain": order.customer.email.split("@")[-1] if "@" in order.customer.email else "",
        "line_items": [{"title": i.title, "quantity": i.quantity, "price": i.price}
                       for i in order.line_items],
        "shipping_country": order.shipping_address.country if order.shipping_address else None,
        "billing_country": order.billing_address.country if order.billing_address else None,
    }

    try:
        result = await ai.call_llm(
            system=_SYSTEM_PROMPT,
            user=f"Analyze this order:\n{json.dumps(order_summary, indent=2)}"
        )
        if result:
            parsed = json.loads(result.strip())
            _valid_recommendations = {"approve", "review", "reject"}
            raw_score = int(parsed.get("risk_score", 0))
            raw_reco = parsed.get("recommendation", "review")
            return AnomalyReport(
                order_id=order.order_id,
                flags=parsed.get("flags", []),
                risk_score=max(0, min(100, raw_score)),
                recommendation=raw_reco if raw_reco in _valid_recommendations else "review",
                reasoning=parsed.get("reasoning", ""),
            )
    except Exception as e:
        log.warning("anomaly_ai_failed", order_id=order.order_id, error=str(e))

    # Fallback to rule-based
    return _rule_based_score(order)

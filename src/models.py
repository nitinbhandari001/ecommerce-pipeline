"""Pydantic v2 domain models for the e-commerce pipeline."""
from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


class OrderStatus(StrEnum):
    received = "received"
    validating = "validating"
    checking_inventory = "checking_inventory"
    detecting_anomalies = "detecting_anomalies"
    generating_invoice = "generating_invoice"
    notifying = "notifying"
    completed = "completed"
    flagged_for_review = "flagged_for_review"
    failed = "failed"


class Address(BaseModel):
    model_config = ConfigDict(frozen=True)

    address1: str
    address2: str | None = None
    city: str
    province: str | None = None
    country: str
    zip: str | None = None
    phone: str | None = None


class Customer(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    email: str
    first_name: str
    last_name: str
    orders_count: int = 0
    total_spent: float = 0.0
    created_at: str | None = None
    tags: list[str] = []


class LineItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    product_id: str | None = None
    variant_id: str | None = None
    title: str
    quantity: int
    price: float
    sku: str | None = None
    requires_shipping: bool = True


class Order(BaseModel):
    model_config = ConfigDict(frozen=True)

    order_id: str
    order_number: str
    customer: Customer
    line_items: list[LineItem]
    subtotal: float
    tax: float
    total: float
    currency: str = "USD"
    shipping_address: Address | None = None
    billing_address: Address | None = None
    financial_status: str = "pending"
    fulfillment_status: str | None = None
    created_at: str
    note: str | None = None
    tags: list[str] = []
    source: str = "shopify"


class Product(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    sku: str | None = None
    price: float
    inventory_quantity: int
    category: str
    vendor: str
    weight_grams: int = 0


class InventoryCheckItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    product_id: str | None
    title: str
    requested: int
    available: int
    status: str  # "ok" | "backorder" | "unknown"


class InventoryResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str  # "ok" | "partial" | "fail"
    items: list[InventoryCheckItem]


class AnomalyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    order_id: str
    flags: list[str]
    risk_score: int  # 0-100
    recommendation: str  # "approve" | "review" | "reject"
    reasoning: str


class Invoice(BaseModel):
    model_config = ConfigDict(frozen=True)

    invoice_number: str
    order_id: str
    customer_name: str
    line_items: list[LineItem]
    subtotal: float
    tax_rate: float
    tax_amount: float
    total: float
    generated_at: str
    file_path: str | None = None


class PipelineResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    order_id: str
    status: OrderStatus
    validation_passed: bool
    validation_errors: list[str] = []
    inventory_result: InventoryResult | None = None
    anomaly_report: AnomalyReport | None = None
    invoice: Invoice | None = None
    notifications_sent: list[str] = []
    processing_time_ms: float
    stage_times_ms: dict[str, float] = {}
    error: str | None = None

import pytest
from src.pipeline.processor import process_order
from src.models import OrderStatus
import copy


@pytest.mark.asyncio
async def test_full_pipeline_normal_order(container, sample_order_payload):
    result = await process_order(sample_order_payload, container)
    assert result.validation_passed is True
    assert result.status in (OrderStatus.completed, OrderStatus.flagged_for_review)
    assert result.processing_time_ms > 0


@pytest.mark.asyncio
async def test_pipeline_flags_anomaly(container, sample_order_payload):
    payload = copy.deepcopy(sample_order_payload)
    payload["total_price"] = "2000.00"
    payload["subtotal_price"] = "2000.00"
    payload["customer"]["orders_count"] = 0
    payload["customer"]["total_spent"] = "0"
    result = await process_order(payload, container)
    assert result.anomaly_report is not None
    assert result.anomaly_report.risk_score > 0


@pytest.mark.asyncio
async def test_pipeline_handles_validation_failure(container):
    bad_payload = {"id": "bad-001", "line_items": []}
    result = await process_order(bad_payload, container)
    assert result.validation_passed is False
    assert result.status == OrderStatus.failed
    assert len(result.validation_errors) > 0


@pytest.mark.asyncio
async def test_pipeline_timing_recorded(container, sample_order_payload):
    result = await process_order(sample_order_payload, container)
    assert result.processing_time_ms > 0
    assert "validate" in result.stage_times_ms

import pytest
import copy


@pytest.mark.asyncio
async def test_process_order_endpoint(api_client, sample_order_payload):
    resp = await api_client.post("/api/orders/process", json=sample_order_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "order_id" in data
    assert "status" in data


@pytest.mark.asyncio
async def test_list_orders_endpoint(api_client, sample_order_payload):
    # Process one first
    await api_client.post("/api/orders/process", json=sample_order_payload)
    resp = await api_client.get("/api/orders")
    assert resp.status_code == 200
    assert resp.json()["count"] >= 1


@pytest.mark.asyncio
async def test_approve_flagged_order(api_client, sample_order_payload):
    payload = copy.deepcopy(sample_order_payload)
    payload["total_price"] = "3000.00"
    payload["subtotal_price"] = "3000.00"
    payload["customer"]["orders_count"] = 0
    payload["customer"]["total_spent"] = "0"
    result = await api_client.post("/api/orders/process", json=payload)
    order_id = result.json()["order_id"]
    resp = await api_client.post(f"/api/orders/{order_id}/approve")
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_reject_flagged_order(api_client, sample_order_payload):
    payload = copy.deepcopy(sample_order_payload)
    payload["id"] = "reject-test-002"
    await api_client.post("/api/orders/process", json=payload)
    resp = await api_client.post("/api/orders/reject-test-002/reject")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_health_check(api_client):
    resp = await api_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "services" in data

"""Async-safe in-memory store for orders and pipeline results."""
from __future__ import annotations

import asyncio
from pathlib import Path

import structlog

from ..models import Order, OrderStatus, PipelineResult

log = structlog.get_logger(__name__)


class OrderStore:
    def __init__(self, persist_dir: str | None = None) -> None:
        self._orders: dict[str, Order] = {}
        self._results: dict[str, PipelineResult] = {}
        self._statuses: dict[str, OrderStatus] = {}
        self._lock = asyncio.Lock()
        self._persist_dir: Path | None = Path(persist_dir) if persist_dir else None
        if self._persist_dir:
            self._persist_dir.mkdir(parents=True, exist_ok=True)

    async def save_order(self, order: Order) -> None:
        async with self._lock:
            self._orders[order.order_id] = order
            self._statuses[order.order_id] = OrderStatus.received

    async def update_status(self, order_id: str, status: OrderStatus) -> None:
        async with self._lock:
            self._statuses[order_id] = status

    async def save_result(self, result: PipelineResult) -> None:
        async with self._lock:
            self._results[result.order_id] = result
            self._statuses[result.order_id] = result.status
            if self._persist_dir:
                path = self._persist_dir / f"{result.order_id}.json"
                content = result.model_dump_json(indent=2)
                await asyncio.to_thread(path.write_text, content, encoding="utf-8")

    async def get_order(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)

    async def get_result(self, order_id: str) -> PipelineResult | None:
        return self._results.get(order_id)

    async def get_status(self, order_id: str) -> OrderStatus | None:
        return self._statuses.get(order_id)

    async def is_processed(self, order_id: str) -> bool:
        """Idempotency check — has this order already reached a terminal state?"""
        async with self._lock:
            status = self._statuses.get(order_id)
            return status in (
                OrderStatus.completed,
                OrderStatus.flagged_for_review,
                OrderStatus.failed,
            )

    async def list_results(self) -> list[PipelineResult]:
        return list(self._results.values())

    async def approve_order(self, order_id: str) -> bool:
        """Human-in-the-loop: approve a flagged order."""
        async with self._lock:
            if order_id not in self._results:
                return False
            result = self._results[order_id]
            updated = result.model_copy(update={"status": OrderStatus.completed})
            self._results[order_id] = updated
            self._statuses[order_id] = OrderStatus.completed
            log.info("order_approved", order_id=order_id)
            return True

    async def reject_order(self, order_id: str) -> bool:
        """Human-in-the-loop: reject a flagged order."""
        async with self._lock:
            if order_id not in self._results:
                return False
            result = self._results[order_id]
            updated = result.model_copy(update={"status": OrderStatus.failed})
            self._results[order_id] = updated
            self._statuses[order_id] = OrderStatus.failed
            log.info("order_rejected", order_id=order_id)
            return True

    @property
    def count(self) -> int:
        return len(self._orders)

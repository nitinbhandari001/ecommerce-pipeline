"""Google Sheets order logging with CSV fallback."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

import structlog

log = structlog.get_logger(__name__)


class SheetsService:
    def __init__(self, service_account_json: str, sheet_id: str) -> None:
        self._sheet_id = sheet_id
        self._client = None
        sa_path = Path(service_account_json)
        if sheet_id and sa_path.exists():
            try:
                import gspread
                from google.oauth2.service_account import Credentials

                scopes = ["https://www.googleapis.com/auth/spreadsheets"]
                creds = Credentials.from_service_account_file(str(sa_path), scopes=scopes)
                self._client = gspread.authorize(creds)
            except Exception as exc:
                log.warning("sheets_init_failed", error=str(exc))
        self._csv_path = Path("data") / "orders" / "order_log.csv"

    async def log_order(
        self,
        order_id: str,
        customer: str,
        total: float,
        status: str,
    ) -> bool:
        row = [
            order_id,
            customer,
            f"${total:.2f}",
            status,
            datetime.now(timezone.utc).isoformat(),
        ]
        if self._client:
            try:
                sheet = self._client.open_by_key(self._sheet_id).sheet1
                sheet.append_row(row)
                return True
            except Exception as exc:
                log.warning("sheets_append_failed", order_id=order_id, error=str(exc))

        # CSV fallback
        try:
            self._csv_path.parent.mkdir(parents=True, exist_ok=True)
            write_header = not self._csv_path.exists()
            with self._csv_path.open("a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if write_header:
                    writer.writerow(["order_id", "customer", "total", "status", "timestamp"])
                writer.writerow(row)
            return True
        except Exception as exc:
            log.warning("sheets_csv_fallback_failed", error=str(exc))
            return False

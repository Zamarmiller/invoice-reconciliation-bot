"""Core data types. Money is always Decimal, never float."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum


class InvoiceStatus(str, Enum):
    APPROVED = "approved"
    PENDING = "pending"
    REJECTED = "rejected"


def period_bounds(period: str) -> tuple[date, date]:
    """Return the inclusive (start, end) dates of a quarter like ``2026-Q1``."""
    try:
        year_s, quarter_s = period.strip().upper().split("-Q")
        year, quarter = int(year_s), int(quarter_s)
    except ValueError as exc:
        raise ValueError(f"Invalid period {period!r}; expected format YYYY-Qn") from exc
    if not 1 <= quarter <= 4:
        raise ValueError(f"Invalid quarter in period {period!r}")

    start = date(year, 3 * (quarter - 1) + 1, 1)
    next_start = date(year + 1, 1, 1) if quarter == 4 else date(year, 3 * quarter + 1, 1)
    return start, next_start - timedelta(days=1)


@dataclass(frozen=True)
class BudgetLine:
    code: str
    department: str
    category: str
    period: str
    allocated: Decimal

    def covers(self, day: date) -> bool:
        start, end = period_bounds(self.period)
        return start <= day <= end


@dataclass(frozen=True)
class Invoice:
    invoice_id: str
    vendor: str
    invoice_date: date
    budget_code: str
    amount: Decimal
    status: InvoiceStatus

"""CSV loaders with row-level validation."""

from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from recon_bot.models import BudgetLine, Invoice, InvoiceStatus, period_bounds

BUDGET_COLUMNS = {"budget_code", "department", "category", "period", "allocated"}
INVOICE_COLUMNS = {"invoice_id", "vendor", "invoice_date", "budget_code", "amount", "status"}


class DataError(ValueError):
    """Raised when an input file is malformed."""


def _read_rows(path: Path, required: set[str]) -> list[tuple[int, dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise DataError(f"{path.name}: missing columns {sorted(missing)}")
        # Row 1 is the header, so data starts on line 2.
        # Extra unnamed columns land under key None; ignore them.
        return [
            (i, {k: (v or "").strip() for k, v in row.items() if k is not None})
            for i, row in enumerate(reader, 2)
        ]


def _money(value: str, where: str) -> Decimal:
    try:
        return Decimal(value.replace(",", "").replace("$", ""))
    except InvalidOperation as exc:
        raise DataError(f"{where}: invalid amount {value!r}") from exc


def load_budget(path: str | Path) -> list[BudgetLine]:
    path = Path(path)
    lines: list[BudgetLine] = []
    seen: set[str] = set()
    for lineno, row in _read_rows(path, BUDGET_COLUMNS):
        where = f"{path.name}:{lineno}"
        code = row["budget_code"]
        if code in seen:
            raise DataError(f"{where}: duplicate budget_code {code!r}")
        seen.add(code)
        try:
            period_bounds(row["period"])
        except ValueError as exc:
            raise DataError(f"{where}: {exc}") from exc
        lines.append(
            BudgetLine(
                code=code,
                department=row["department"],
                category=row["category"],
                period=row["period"].upper(),
                allocated=_money(row["allocated"], where),
            )
        )
    return lines


def load_invoices(path: str | Path) -> list[Invoice]:
    path = Path(path)
    invoices: list[Invoice] = []
    for lineno, row in _read_rows(path, INVOICE_COLUMNS):
        where = f"{path.name}:{lineno}"
        try:
            invoice_date = date.fromisoformat(row["invoice_date"])
        except ValueError as exc:
            raise DataError(f"{where}: invalid date {row['invoice_date']!r}") from exc
        try:
            status = InvoiceStatus(row["status"].lower())
        except ValueError as exc:
            raise DataError(f"{where}: unknown status {row['status']!r}") from exc
        invoices.append(
            Invoice(
                invoice_id=row["invoice_id"],
                vendor=row["vendor"],
                invoice_date=invoice_date,
                budget_code=row["budget_code"],
                amount=_money(row["amount"], where),
                status=status,
            )
        )
    return invoices

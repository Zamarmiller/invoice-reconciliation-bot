"""Render reconciliation results as a text report or CSV."""

from __future__ import annotations

import csv
from pathlib import Path

from recon_bot.reconcile import ReconciliationResult


def _money(value) -> str:
    return f"{value:,.2f}"


def format_text(result: ReconciliationResult) -> str:
    headers = ["Code", "Department", "Category", "Allocated", "Approved", "Pending", "Remaining", "Used"]
    rows = [
        [
            s.line.code,
            s.line.department,
            s.line.category,
            _money(s.line.allocated),
            _money(s.approved),
            _money(s.pending),
            _money(s.remaining),
            f"{s.utilization:.0%}" if s.utilization.is_finite() else "n/a",
        ]
        for s in result.summaries
    ]
    widths = [max(len(str(c)) for c in col) for col in zip(headers, *rows)]
    numeric = set(range(3, len(headers)))

    def fmt(row: list[str]) -> str:
        return "  ".join(
            cell.rjust(w) if i in numeric else cell.ljust(w)
            for i, (cell, w) in enumerate(zip(row, widths))
        )

    out = ["BUDGET SUMMARY", fmt(headers), "  ".join("-" * w for w in widths)]
    out += [fmt(r) for r in rows]
    out.append("")
    if result.issues:
        out.append(f"ISSUES ({len(result.issues)})")
        out += [f"  [{i.type.value}] {i.message}" for i in result.issues]
    else:
        out.append("No issues found.")
    return "\n".join(out)


def write_issues_csv(result: ReconciliationResult, path: str | Path) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["type", "budget_code", "invoice_id", "message"])
        for i in result.issues:
            writer.writerow([i.type.value, i.budget_code or "", i.invoice_id or "", i.message])

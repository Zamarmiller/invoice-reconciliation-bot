"""Reconciliation engine: match invoices to budget lines and flag exceptions."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Iterable

from recon_bot.models import BudgetLine, Invoice, InvoiceStatus


class IssueType(str, Enum):
    INVALID_AMOUNT = "invalid_amount"
    DUPLICATE_INVOICE = "duplicate_invoice"
    UNKNOWN_BUDGET_CODE = "unknown_budget_code"
    OUT_OF_PERIOD = "out_of_period"
    OVER_BUDGET = "over_budget"
    NEAR_LIMIT = "near_limit"


@dataclass(frozen=True)
class Issue:
    type: IssueType
    message: str
    budget_code: str | None = None
    invoice_id: str | None = None


@dataclass
class LineSummary:
    line: BudgetLine
    approved: Decimal = Decimal("0")
    pending: Decimal = Decimal("0")
    invoice_ids: list[str] = field(default_factory=list)

    @property
    def committed(self) -> Decimal:
        return self.approved + self.pending

    @property
    def remaining(self) -> Decimal:
        return self.line.allocated - self.committed

    @property
    def utilization(self) -> Decimal:
        if self.line.allocated <= 0:
            return Decimal("0") if self.committed == 0 else Decimal("Infinity")
        return self.committed / self.line.allocated


@dataclass
class ReconciliationResult:
    summaries: list[LineSummary]
    issues: list[Issue]

    @property
    def has_issues(self) -> bool:
        return bool(self.issues)


def reconcile(
    budget: Iterable[BudgetLine],
    invoices: Iterable[Invoice],
    warn_threshold: Decimal = Decimal("0.90"),
) -> ReconciliationResult:
    """Reconcile invoices against budget lines.

    Approved and pending invoices both count toward a line's committed spend.
    Rejected invoices are ignored. Invoices that fail a check (bad amount,
    duplicate, unknown code, out of period) are flagged and *not* counted.
    """
    summaries = {line.code: LineSummary(line) for line in budget}
    issues: list[Issue] = []
    seen_ids: set[str] = set()
    seen_fingerprints: dict[tuple[str, object, Decimal], str] = {}

    for inv in invoices:
        if inv.status is InvoiceStatus.REJECTED:
            continue

        if inv.amount <= 0:
            issues.append(Issue(IssueType.INVALID_AMOUNT,
                                f"{inv.invoice_id}: amount must be positive (got {inv.amount})",
                                inv.budget_code, inv.invoice_id))
            continue

        if inv.invoice_id in seen_ids:
            issues.append(Issue(IssueType.DUPLICATE_INVOICE,
                                f"{inv.invoice_id}: invoice ID appears more than once",
                                inv.budget_code, inv.invoice_id))
            continue
        seen_ids.add(inv.invoice_id)

        fingerprint = (inv.vendor.casefold(), inv.invoice_date, inv.amount)
        if fingerprint in seen_fingerprints:
            original = seen_fingerprints[fingerprint]
            issues.append(Issue(IssueType.DUPLICATE_INVOICE,
                                f"{inv.invoice_id}: likely duplicate of {original} "
                                f"(same vendor, date and amount)",
                                inv.budget_code, inv.invoice_id))
            continue
        seen_fingerprints[fingerprint] = inv.invoice_id

        summary = summaries.get(inv.budget_code)
        if summary is None:
            issues.append(Issue(IssueType.UNKNOWN_BUDGET_CODE,
                                f"{inv.invoice_id}: budget code {inv.budget_code!r} not found",
                                inv.budget_code, inv.invoice_id))
            continue

        if not summary.line.covers(inv.invoice_date):
            issues.append(Issue(IssueType.OUT_OF_PERIOD,
                                f"{inv.invoice_id}: dated {inv.invoice_date} but "
                                f"{inv.budget_code} covers {summary.line.period}",
                                inv.budget_code, inv.invoice_id))
            continue

        if inv.status is InvoiceStatus.APPROVED:
            summary.approved += inv.amount
        else:
            summary.pending += inv.amount
        summary.invoice_ids.append(inv.invoice_id)

    for s in summaries.values():
        if s.committed > s.line.allocated:
            issues.append(Issue(IssueType.OVER_BUDGET,
                                f"{s.line.code} ({s.line.category}): over budget by "
                                f"{-s.remaining:,.2f}",
                                s.line.code))
        elif s.committed > 0 and s.utilization >= warn_threshold:
            issues.append(Issue(IssueType.NEAR_LIMIT,
                                f"{s.line.code} ({s.line.category}): "
                                f"{s.utilization:.1%} of budget committed",
                                s.line.code))

    return ReconciliationResult(summaries=list(summaries.values()), issues=issues)

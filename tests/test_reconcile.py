import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from recon_bot.cli import main
from recon_bot.loader import DataError, load_budget, load_invoices
from recon_bot.models import BudgetLine, Invoice, InvoiceStatus, period_bounds
from recon_bot.reconcile import IssueType, reconcile

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "sample_data"

D = Decimal


def line(code="BC-1", allocated="1000", period="2026-Q1"):
    return BudgetLine(code, "Dept", "Cat", period, D(allocated))


def inv(invoice_id, amount, code="BC-1", vendor="Vendor A", day=date(2026, 2, 1),
        status=InvoiceStatus.APPROVED):
    return Invoice(invoice_id, vendor, day, code, D(amount), status)


def issue_types(result):
    return [i.type for i in result.issues]


class PeriodTests(unittest.TestCase):
    def test_quarter_bounds(self):
        self.assertEqual(period_bounds("2026-Q1"), (date(2026, 1, 1), date(2026, 3, 31)))
        self.assertEqual(period_bounds("2024-Q1")[1], date(2024, 3, 31))
        self.assertEqual(period_bounds("2026-Q4"), (date(2026, 10, 1), date(2026, 12, 31)))

    def test_invalid_period(self):
        for bad in ("2026", "2026-Q5", "Q1-2026"):
            with self.assertRaises(ValueError):
                period_bounds(bad)


class ReconcileTests(unittest.TestCase):
    def test_clean_run_has_no_issues(self):
        result = reconcile([line()], [inv("I1", "300"), inv("I2", "200", status=InvoiceStatus.PENDING)])
        self.assertEqual(result.issues, [])
        s = result.summaries[0]
        self.assertEqual((s.approved, s.pending, s.remaining), (D("300"), D("200"), D("500")))

    def test_over_budget(self):
        result = reconcile([line()], [inv("I1", "900"), inv("I2", "200")])
        self.assertEqual(issue_types(result), [IssueType.OVER_BUDGET])

    def test_near_limit_respects_threshold(self):
        invoices = [inv("I1", "920")]
        self.assertEqual(issue_types(reconcile([line()], invoices)), [IssueType.NEAR_LIMIT])
        self.assertEqual(issue_types(reconcile([line()], invoices, warn_threshold=D("0.95"))), [])

    def test_duplicate_by_fingerprint_is_not_counted(self):
        result = reconcile([line()], [inv("I1", "100"), inv("I2", "100", vendor="vendor a")])
        self.assertEqual(issue_types(result), [IssueType.DUPLICATE_INVOICE])
        self.assertEqual(result.summaries[0].approved, D("100"))

    def test_duplicate_invoice_id(self):
        result = reconcile([line()], [inv("I1", "100"), inv("I1", "250")])
        self.assertEqual(issue_types(result), [IssueType.DUPLICATE_INVOICE])

    def test_unknown_code_out_of_period_and_invalid_amount(self):
        result = reconcile([line()], [
            inv("I1", "100", code="BC-404"),
            inv("I2", "100", day=date(2026, 4, 1)),
            inv("I3", "0"),
        ])
        self.assertEqual(issue_types(result), [
            IssueType.UNKNOWN_BUDGET_CODE, IssueType.OUT_OF_PERIOD, IssueType.INVALID_AMOUNT,
        ])
        self.assertEqual(result.summaries[0].committed, D("0"))

    def test_rejected_invoices_are_ignored(self):
        result = reconcile([line()], [inv("I1", "5000", status=InvoiceStatus.REJECTED)])
        self.assertEqual(result.issues, [])
        self.assertEqual(result.summaries[0].committed, D("0"))


class SampleDataTests(unittest.TestCase):
    def test_sample_data_flags_expected_issues(self):
        result = reconcile(load_budget(SAMPLE_DIR / "budget.csv"), load_invoices(SAMPLE_DIR / "invoices.csv"))
        flagged = {(i.type, i.invoice_id or i.budget_code) for i in result.issues}
        self.assertEqual(flagged, {
            (IssueType.DUPLICATE_INVOICE, "INV-1010"),
            (IssueType.UNKNOWN_BUDGET_CODE, "INV-1011"),
            (IssueType.OUT_OF_PERIOD, "INV-1013"),
            (IssueType.OVER_BUDGET, "BC-110"),
            (IssueType.OVER_BUDGET, "BC-210"),
            (IssueType.NEAR_LIMIT, "BC-200"),
        })

    def test_cli_runs_and_writes_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "issues.csv"
            self.assertEqual(main(["--issues-csv", str(out)]), 0)
            self.assertEqual(main(["--fail-on-issues"]), 1)
            self.assertEqual(len(out.read_text(encoding="utf-8").strip().splitlines()), 7)


class LoaderTests(unittest.TestCase):
    def test_missing_column_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "budget.csv"
            path.write_text("budget_code,department\nBC-1,Ops\n", encoding="utf-8")
            with self.assertRaises(DataError):
                load_budget(path)

    def test_bad_amount_reports_line_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invoices.csv"
            path.write_text(
                "invoice_id,vendor,invoice_date,budget_code,amount,status\n"
                "I1,V,2026-01-01,BC-1,abc,approved\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(DataError, "invoices.csv:2"):
                load_invoices(path)


if __name__ == "__main__":
    unittest.main()

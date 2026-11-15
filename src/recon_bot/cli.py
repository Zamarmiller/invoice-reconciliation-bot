"""Command-line entry point: ``recon-bot`` or ``python -m recon_bot``."""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

from recon_bot.loader import DataError, load_budget, load_invoices
from recon_bot.reconcile import reconcile
from recon_bot.report import format_text, write_issues_csv

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "sample_data"


def _threshold(value: str) -> Decimal:
    try:
        d = Decimal(value)
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError(f"not a number: {value!r}") from exc
    if not 0 < d <= 1:
        raise argparse.ArgumentTypeError("must be between 0 and 1 (e.g. 0.9)")
    return d


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="recon-bot", description="Reconcile invoices against budget lines.")
    p.add_argument("--budget", type=Path, default=SAMPLE_DIR / "budget.csv", help="budget CSV path")
    p.add_argument("--invoices", type=Path, default=SAMPLE_DIR / "invoices.csv", help="invoices CSV path")
    p.add_argument("--warn-threshold", type=_threshold, default=Decimal("0.90"),
                   help="flag lines at or above this utilization (default 0.90)")
    p.add_argument("--issues-csv", type=Path, help="also write issues to this CSV file")
    p.add_argument("--fail-on-issues", action="store_true", help="exit with status 1 if any issues are found")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        budget = load_budget(args.budget)
        invoices = load_invoices(args.invoices)
    except (OSError, DataError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    result = reconcile(budget, invoices, warn_threshold=args.warn_threshold)
    print(format_text(result))
    if args.issues_csv:
        write_issues_csv(result, args.issues_csv)
        print(f"\nIssues written to {args.issues_csv}")
    return 1 if args.fail_on_issues and result.has_issues else 0


if __name__ == "__main__":
    raise SystemExit(main())

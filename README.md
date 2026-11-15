# Invoice Reconciliation Bot

![tests](https://github.com/Zamarmiller/invoice-reconciliation-bot/actions/workflows/tests.yml/badge.svg)

A small Python tool that reconciles vendor invoices against departmental budget lines and flags anything that needs a human to look at it.

> **All data in this repo is fictional.** Vendors, budget codes, and amounts were invented for demonstration. This is a generic portfolio project, not based on any real client's data or business rules.

## What it does

You give it two CSV files: a budget and a list of invoices. It matches each invoice to a budget line, totals the spend, and reports:

| Check | What gets flagged |
|---|---|
| **Over budget** | Approved + pending spend on a line exceeds its allocation |
| **Near limit** | A line has reached the warning threshold (default 90%) |
| **Duplicate invoice** | A repeated invoice ID, or the same vendor, date, and amount twice |
| **Unknown budget code** | The invoice points at a code that isn't in the budget |
| **Out of period** | The invoice date falls outside the budget line's quarter |
| **Invalid amount** | Zero or negative amounts |

Flagged invoices are left out of the totals so they don't inflate spend. Rejected invoices are ignored.

## Quick start

Requires Python 3.10 or newer. There are no third-party dependencies.

```bash
git clone https://github.com/Zamarmiller/invoice-reconciliation-bot.git
cd invoice-reconciliation-bot
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .

recon-bot                        # runs against sample_data/
```

The output is a budget summary table followed by a list of issues. On the sample data it flags two over-budget lines, one near-limit line, a duplicate invoice, an unknown budget code, and an out-of-period invoice.

### Options

```bash
recon-bot --budget path/to/budget.csv --invoices path/to/invoices.csv
recon-bot --warn-threshold 0.8         # warn at 80% instead of 90%
recon-bot --issues-csv issues.csv      # also export issues to CSV
recon-bot --fail-on-issues             # exit 1 if anything is flagged (useful in CI/automation)
```

## Input format

**budget.csv**

```csv
budget_code,department,category,period,allocated
BC-100,Marketing,Advertising,2026-Q1,15000.00
```

**invoices.csv**

```csv
invoice_id,vendor,invoice_date,budget_code,amount,status
INV-1001,Acme Media Group,2026-01-08,BC-100,4200.00,approved
```

- `period` is a calendar quarter: `YYYY-Q1` through `YYYY-Q4`
- `invoice_date` is ISO format (`YYYY-MM-DD`)
- `status` is `approved`, `pending`, or `rejected`
- Malformed rows fail fast with the file name and line number

## Project layout

```
src/recon_bot/
  models.py      data types (BudgetLine, Invoice) and period handling
  loader.py      CSV parsing and validation
  reconcile.py   matching logic and exception checks
  report.py      text table and CSV export
  cli.py         command-line interface
sample_data/     fictional budget and invoices
tests/           unit tests (standard-library unittest)
```

## Running tests

```bash
python -m unittest discover -s tests -v
```

The tests also run on GitHub Actions for Python 3.10, 3.12, and 3.13.

## Design notes

- **Decimal, not float.** Money is handled with `decimal.Decimal` throughout to avoid rounding errors.
- **Flag, don't drop silently.** Every invoice that's excluded from the totals produces an issue explaining why.
- **No dependencies.** Standard library only, so it's easy to run anywhere.

## Possible extensions

- Fuzzy vendor-name matching (e.g. "Acme Media" vs "Acme Media Group")
- Monthly or custom budget periods
- Excel input/output
- Email or Slack summaries of flagged items

## License

[MIT](LICENSE)

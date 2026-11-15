# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project

A portfolio project: a CLI tool that reconciles vendor invoices against budget lines and flags exceptions (over budget, near limit, duplicates, unknown codes, out-of-period, invalid amounts). Python 3.10+, standard library only.

## Data policy (important)

- This repo is **public**. Use **fake sample data only**.
- Never add real client names, vendors, invoice numbers, amounts, budget codes, or client-specific business rules, even as examples or in tests.
- New sample data should use clearly fictional vendors (e.g. "Acme", "Nimbus Cloud Inc.") and the `BC-xxx` / `INV-xxxx` code formats.
- Real data, if ever used locally, belongs in `data/` or `private/`. Both are gitignored. Check `git status` before committing.

## Commands

```bash
pip install -e .                               # install (editable)
python -m recon_bot                            # run against sample_data/
python -m unittest discover -s tests -v        # run tests
```

Without installing: set `PYTHONPATH=src`.

## Layout

- `src/recon_bot/models.py`: `BudgetLine`, `Invoice`, `InvoiceStatus`, `period_bounds()`
- `src/recon_bot/loader.py`: CSV loading. Raises `DataError` with `file:line` context.
- `src/recon_bot/reconcile.py`: `reconcile()` returns a `ReconciliationResult` (per-line summaries plus a list of `Issue`s)
- `src/recon_bot/report.py`: text table and CSV export
- `src/recon_bot/cli.py`: argparse entry point (`recon-bot`)
- `tests/test_reconcile.py`: unittest suite, including an end-to-end check on `sample_data/`

## Conventions

- Money is always `Decimal`. Never use `float` for amounts.
- Invoices that fail a check are excluded from totals **and** reported as an `Issue`. Nothing is dropped silently.
- Adding a new check means: add an `IssueType`, implement it in `reconcile()`, add a unit test, and update the table in README.md.
- If you change `sample_data/`, update `SampleDataTests` so the expected flagged set still matches.
- Keep it dependency-free unless there's a strong reason to add one.
- CI (`.github/workflows/tests.yml`) runs the tests on Python 3.10, 3.12, and 3.13.

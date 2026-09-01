# Contributing

CommerceIQ favors small, reproducible changes with explicit metric semantics.

1. Create a focused branch from `main`.
2. Keep raw data and credentials outside version control.
3. Add or update tests for behavioral changes.
4. Run `python -m ruff check src scripts tests`.
5. Run `python -m pytest -q`.
6. Document changes to data grain, filters, or KPI definitions.

Generated analytical outputs should only be updated after the complete audit,
cleaning, database-load, and analytics sequence succeeds.

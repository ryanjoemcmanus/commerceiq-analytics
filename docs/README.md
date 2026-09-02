# CommerceIQ Documentation

> **Independent portfolio project:** Not affiliated with, endorsed by, or
> created for CommerceIQ, Inc.

This directory connects the business narrative to the metric definitions,
relational model, transformation rules, and reproducible analytical evidence.

## Start Here

1. [Executive summary](executive_summary.md) — concise marketplace findings and
   recommended actions.
2. [Architecture](architecture.md) — end-to-end data flow and entity-relationship
   diagram.
3. [Analysis findings](analysis_findings.md) — detailed observed patterns and
   interpretation limits.
4. [Conclusion](conclusion.md) — decision-oriented synthesis and next steps.

## Technical Reference

| Document | Purpose |
|---|---|
| [Data model](data_model.md) | Table grains, keys, relationships, and design decisions |
| [Cleaning rules](cleaning_rules.md) | Source-to-processed transformation contract |
| [KPI definitions](kpi_definitions.md) | Filters, formulas, grains, and interpretation limits |
| [Database setup](database_setup.md) | PostgreSQL installation and local configuration |

## Traceability

Metric logic is defined in `sql/`, reusable validation and transformation logic
lives in `src/`, and executable entry points live in `scripts/`. The notebooks,
dashboard, reports, and presentation consume those validated outputs rather than
redefining business metrics independently.

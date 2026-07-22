# CommerceIQ Power BI Dashboard

This directory contains the stakeholder-facing reporting layer for CommerceIQ.
The dashboard uses validated aggregate outputs from the PostgreSQL analytics
pipeline; it does not calculate business metrics directly from the raw Olist
CSV files.

## Files

- `commerceiq_dashboard.pbix` - interactive three-page Power BI Desktop report.
- `data/commerceiq-dashboard-source.xlsx` - portable dashboard source workbook
  containing the ten validated analytical extracts.
- `exports/commerceiq_dashboard.pdf` - static three-page portfolio export.
- `../images/commerceiq-dashboard-*.png` - rendered page previews used by the
  repository documentation.

## Report Pages

### Executive Overview

Provides the headline marketplace view: delivered item GMV, delivered orders,
delivered AOV, on-time delivery rate, and the monthly delivered-GMV trend. The
month field is typed as a Power BI Date so the horizontal axis displays calendar
labels rather than Excel serial values.

### Operations & Experience

Compares low-review rates across delivery-timing bands and shows the distribution
of order statuses. This page supports the operational recommendation to prevent
late deliveries and proactively manage delivery exceptions.

![Operations and experience dashboard](../images/commerceiq-dashboard-2.png)

### Customers & Markets

Shows delivered GMV by customer state and payment value by payment method. It
highlights the commercial concentration in Brazil's largest states and the
importance of credit-card and installment behavior.

![Customers and markets dashboard](../images/commerceiq-dashboard-3.png)

## Metric Semantics

- Delivered GMV is item price on delivered orders; freight is excluded.
- Delivered AOV is delivered GMV divided by delivered orders.
- On-time delivery compares calendar dates and ignores time of day.
- Low reviews are order-level average review scores less than or equal to 2.
- Customer identity is based on `customer_unique_id`.
- Payment-method order counts are not additive because an order may have more
  than one payment record.

The full definitions and interpretation limits are in
[`../docs/kpi_definitions.md`](../docs/kpi_definitions.md).

## Open and Refresh

1. Run the audit, cleaning, database load, and analytics commands from the main
   README when rebuilding the project from raw data.
2. Open `commerceiq_dashboard.pbix` in Power BI Desktop.
3. If the portable source must be rebuilt, replace the workbook tables using the
   validated CSVs generated in `reports/analytics/`, preserving table names and
   column types.
4. Select **Refresh** in Power BI and confirm that every page renders without
   errors before saving or exporting.

The dashboard source tables are intentionally pre-aggregated at different
business grains. They should remain disconnected unless a relationship is
explicitly required and its one-to-many cardinality has been validated.

## Portfolio Review

The PDF export provides a no-installation preview. Use the PBIX for tooltips,
cross-highlighting, sorting, and deeper inspection in Power BI Desktop.

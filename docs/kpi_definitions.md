# CommerceIQ KPI Definitions

Every KPI is calculated at an explicitly documented grain. Payments, reviews,
and order items are aggregated independently before they are joined to orders,
preventing many-to-many joins from inflating values.

## Core Filters and Conventions

- **Delivered commercial metrics** include only `order_status = 'delivered'`.
- **Delivered GMV** is the sum of order-item `price`; freight is excluded and
  reported separately where useful.
- **Order date** is `order_purchase_timestamp`.
- **On-time delivery** means the customer-delivery calendar date is on or before
  the estimated-delivery calendar date. Time-of-day is intentionally ignored
  because the estimate is supplied at date grain.
- **Customer identity** uses `customer_unique_id`, not the order-level
  `customer_id`.
- **Review metrics** first average review records to one value per order.
- Boundary months in 2016 and September–October 2018 are incomplete. The core
  monthly trend view uses January 2017 through August 2018.

## Executive KPIs

| KPI | Definition |
|---|---|
| Total orders | Distinct rows in the order table |
| Delivered orders | Orders whose status is `delivered` |
| Unique customers | Distinct `customer_unique_id` values with an order |
| Active sellers | Distinct sellers attached to a delivered order item |
| Delivered GMV | Sum of item prices on delivered orders |
| Delivered AOV | Delivered GMV ÷ delivered orders |
| Cancellation rate | Canceled orders ÷ all orders |
| On-time delivery rate | On-time delivered orders ÷ delivered orders with both delivery dates |
| Average delivery days | Average elapsed days from purchase timestamp to customer delivery |
| Average review score | Average of the order-level review averages |
| Low-review rate | Reviewed orders with an order-level average score ≤ 2 ÷ reviewed orders |
| Repeat-customer rate | Customers with at least two delivered orders ÷ customers with a delivered order |

## Dimensional Analyses

- Monthly performance is grouped by purchase month.
- Category performance uses delivered category-order grain before category
  aggregation, allowing reviews to be averaged without item-count weighting.
- State performance uses the customer state associated with the order.
- Payment results are grouped by payment record type. An order can use multiple
  payment types, so method-level order counts are not additive.
- Seller scorecards first aggregate to seller-order grain.
- Cohorts use the month of a customer's first delivered order and report
  subsequent distinct monthly activity.

## Interpretation Limits

- GMV is not accounting revenue, profit, or cash collected.
- The public dataset is a historical observation window, not a live feed.
- Associations between delivery timing and reviews do not alone establish
  causality.
- Cohort retention is truncated for recent cohorts and should be compared only
  at common month numbers.
- Geographic results reflect marketplace activity represented in this dataset,
  not total regional market demand.


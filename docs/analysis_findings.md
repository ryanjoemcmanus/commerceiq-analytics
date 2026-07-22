# CommerceIQ Exploratory Business Findings

These findings were generated from the validated PostgreSQL extracts in
`reports/analytics`. They describe the dataset's observed period and should not
be generalized beyond it without additional evidence.

## Executive Snapshot

From September 4, 2016 through October 17, 2018, the dataset contains 99,441
orders, of which 96,478 were delivered. Delivered item GMV totals R$13.22
million and delivered average order value is R$137.04. The overall cancellation
rate is 0.63%, and 93.23% of delivered orders with comparable dates arrived on
or before the estimated calendar date.

The average order-level review score is 4.09, while 14.64% of reviewed orders
have an average score of 2 or lower. Only 3.00% of customers with a delivered
order placed at least two delivered orders during the observation window.

## Findings

### Delivery reliability is closely associated with customer ratings

Orders delivered at least two days early have an average review score of 4.30
and a 9.16% low-review rate. For orders delivered 4–7 days late, the average
score falls to 2.11 and the low-review rate rises to 67.56%. At 8+ days late,
the average score is 1.70 and 79.18% receive a low review.

This relationship is strong enough to make late-delivery prevention and
proactive exception communication priority operational measures. It remains an
association rather than proof that delay alone caused each rating.

### Performance expanded, with identifiable operational stress periods

Within the comparable January 2017–August 2018 trend window, November 2017 was
the peak month for both delivered orders (7,289) and delivered GMV
(R$987,765.37). March 2018 had the lowest on-time rate in that core window at
81.04% and an average review score of 3.75, compared with the overall 4.09.

Capacity and carrier planning should explicitly account for promotional peaks
and periods where demand growth coincides with weaker delivery performance.

### Commercial activity is concentrated by category and geography

The five largest categories contribute 39.83% of delivered GMV, and the ten
largest contribute 62.43%. Health and beauty is the largest category at
R$1.23 million, followed by watches and gifts at R$1.17 million.

São Paulo accounts for 38.33% of delivered GMV. São Paulo, Rio de Janeiro, and
Minas Gerais together account for 63.38%. Geographic concentration makes
regional fulfillment performance commercially important; it also means results
from the largest states can dominate national averages.

### Repeat purchasing is the clearest commercial growth opportunity

97.00% of customers with a delivered order appear in the one-order frequency
band, and the overall repeat-customer rate is 3.00%. Weighted month-one cohort
activity is approximately 0.48% for cohorts with an observable following month.

This supports testing post-purchase lifecycle messaging, category-specific
replenishment campaigns, and service-recovery outreach. The metric should be
treated as observed-window repeat behavior rather than permanent customer churn.

### Credit cards dominate payment value

Credit cards represent 78.34% of payment value, followed by boleto at 17.92%.
The average credit-card payment record uses 3.51 installments. Payment and
installment behavior should therefore remain visible in conversion and cash-flow
analysis rather than being reduced to a single order-level payment label.

## Recommended Actions

1. Create an operational late-order watchlist using estimated delivery dates,
   carrier handoff, seller, and destination state.
2. Review capacity and carrier allocation ahead of high-volume promotional
   periods, using November 2017 and early 2018 as diagnostic case studies.
3. Segment fulfillment KPIs by the highest-GMV states and categories so
   national averages do not hide commercially material exceptions.
4. Test repeat-purchase campaigns with `customer_unique_id`, maintaining a
   delivered-order definition and cohort-aware measurement window.
5. Preserve payment-method and installment detail in future dashboards and
   profitability work.


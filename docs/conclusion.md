# CommerceIQ Project Conclusion

## Decision Summary

CommerceIQ shows that Olist's historical marketplace performance was commercially
meaningful but operationally uneven. The observed period contains 99,441 orders,
including 96,478 delivered orders and R$13.22 million in delivered item GMV.
Most comparable deliveries arrived on time, yet the minority of late deliveries
was strongly associated with poor customer feedback. At the same time, revenue
was concentrated in a small number of states and categories, while repeat
purchasing remained limited.

The strongest business case is therefore not simply to pursue more order volume.
It is to protect customer experience as volume grows, focus operational attention
where GMV is concentrated, and create a deliberate retention program for the
large base of one-time customers.

## Evidence Behind the Conclusion

### 1. Delivery reliability is the clearest experience lever

- The overall on-time delivery rate is 93.23% for delivered orders with
  comparable dates.
- Orders delivered at least two days early have a 9.16% low-review rate and an
  average review score of 4.30.
- Orders delivered four to seven days late have a 67.56% low-review rate and an
  average review score of 2.11.
- Orders delivered eight or more days late have a 79.18% low-review rate and an
  average review score of 1.70.

The pattern does not prove that lateness caused every low rating, but its size and
consistency make delivery exceptions the most actionable operational priority in
this dataset.

### 2. Growth periods require capacity planning

Within the comparable January 2017 through August 2018 trend window, November
2017 reached 7,289 delivered orders and R$987,765.37 in delivered GMV. March 2018
recorded the weakest on-time rate in that window at 81.04%, alongside an average
review score of 3.75. These periods show why GMV and order growth should be
reviewed together with service-level measures.

### 3. Commercial performance is geographically and categorically concentrated

São Paulo contributes 38.33% of delivered GMV, while São Paulo, Rio de Janeiro,
and Minas Gerais together contribute 63.38%. The five largest categories account
for 39.83% of delivered GMV, and the ten largest account for 62.43%.

This concentration creates an efficient prioritization rule: segment late-order,
seller, and carrier monitoring first by the highest-value states and categories,
then expand the same controls across the marketplace.

### 4. Retention is the largest visible commercial opportunity

Only 3.00% of customers with a delivered order placed at least two delivered
orders during the observed period. Approximately 97% fall into the one-order
frequency band, and weighted month-one cohort activity is about 0.48% among
cohorts with an observable following month.

These figures support controlled post-purchase, replenishment, and service-
recovery experiments. They should not be interpreted as permanent churn because
the public dataset covers a finite historical window.

### 5. Payment behavior should remain visible in commercial analysis

Credit cards account for 78.34% of payment value, boleto for 17.92%, and the
average credit-card payment record uses 3.51 installments. Future conversion,
cash-flow, and retention reporting should preserve both payment method and
installment detail.

## Recommended Action Plan

1. Build a daily late-order watchlist using estimated delivery date, carrier
   handoff, seller, and destination state.
2. Establish alert thresholds for on-time delivery and low-review rates, with
   escalation before seasonal or promotional demand peaks.
3. Prioritize operational review in the highest-GMV states and categories.
4. Test cohort-based post-purchase and replenishment campaigns using
   `customer_unique_id` and a delivered-order repeat definition.
5. Track GMV, order volume, delivery reliability, review outcomes, repeat rate,
   and payment mix together rather than optimizing any single KPI in isolation.

## Analytical Boundaries

- Delivered GMV includes item price and excludes freight; it is not net revenue
  or profit.
- The data does not include product cost, marketing spend, customer-acquisition
  cost, or contribution margin.
- Delivery and review results show association, not causal attribution.
- Customer repeat behavior is constrained by the observation window.
- Results describe the public historical Olist dataset and should be revalidated
  before use in a live marketplace.

## Final Assessment

The project supports a focused stakeholder recommendation: protect service
quality while scaling, concentrate operational effort where marketplace value is
highest, and use disciplined retention experiments to convert more first-time
buyers into repeat customers. The accompanying pipelines, PostgreSQL model, SQL
queries, automated tests, Power BI report, and written definitions make that
conclusion reproducible rather than anecdotal.

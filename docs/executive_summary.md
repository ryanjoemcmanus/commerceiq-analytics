# CommerceIQ Executive Summary

## Marketplace Snapshot

The validated Olist observation window contains 99,441 orders from September 4,
2016 through October 17, 2018. Of these, 96,478 were delivered, generating
R$13.22 million in delivered item GMV and a delivered average order value of
R$137.04. The cancellation rate is 0.63%, and 93.23% of delivered orders with
comparable dates arrived on or before the estimated calendar date.

## What Matters Most

Delivery performance is the clearest customer-experience lever in the data.
Orders delivered at least two days early have a 9.16% low-review rate. That rate
rises to 67.56% for orders delivered four to seven days late and 79.18% for
orders delivered eight or more days late. This is an association, not proof of
causation, but it is operationally strong enough to prioritize exception
prevention and communication.

Commercial activity is concentrated. São Paulo contributes 38.33% of delivered
GMV, and São Paulo, Rio de Janeiro, and Minas Gerais together contribute 63.38%.
The five largest categories account for 39.83% of delivered GMV. National
averages can therefore conceal problems in the regions and categories that
matter most financially.

Customer retention is the largest visible growth opportunity. Only 3.00% of
customers with a delivered order placed at least two delivered orders during
the observed period. Credit cards represent 78.34% of payment value, so future
conversion and retention work should preserve payment method and installment
detail.

## Recommended Actions

1. Build a late-order watchlist using estimated delivery date, seller, carrier
   handoff, and destination state.
2. Plan fulfillment capacity before promotional peaks and monitor on-time rate
   alongside GMV rather than after the peak has passed.
3. Segment operational KPIs by the highest-GMV states and categories.
4. Test post-purchase and replenishment campaigns using `customer_unique_id`
   and a delivered-order repeat definition.
5. Track payment method and installments in conversion and cash-flow analysis.

These recommendations are grounded in the historical public dataset and should
be revalidated before applying them to a live marketplace.

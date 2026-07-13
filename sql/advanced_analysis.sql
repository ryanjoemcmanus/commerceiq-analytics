-- CommerceIQ advanced analytical queries.

-- name: delivery_review_relationship
-- grain: One row per delivered-order timing band.
WITH review_by_order AS (
    SELECT order_id, AVG(review_score)::NUMERIC AS average_review_score
    FROM commerceiq.order_reviews
    GROUP BY order_id
),
delivered_orders AS (
    SELECT
        o.order_id,
        (o.order_delivered_customer_date::DATE - o.order_estimated_delivery_date::DATE)
            AS delivery_delay_days,
        r.average_review_score
    FROM commerceiq.orders AS o
    LEFT JOIN review_by_order AS r ON r.order_id = o.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
      AND o.order_estimated_delivery_date IS NOT NULL
),
banded AS (
    SELECT
        order_id,
        delivery_delay_days,
        average_review_score,
        CASE
            WHEN delivery_delay_days <= -2 THEN '2+ days early'
            WHEN delivery_delay_days <= 0 THEN 'on time / 1 day early'
            WHEN delivery_delay_days <= 3 THEN '1–3 days late'
            WHEN delivery_delay_days <= 7 THEN '4–7 days late'
            ELSE '8+ days late'
        END AS delivery_timing_band,
        CASE
            WHEN delivery_delay_days <= -2 THEN 1
            WHEN delivery_delay_days <= 0 THEN 2
            WHEN delivery_delay_days <= 3 THEN 3
            WHEN delivery_delay_days <= 7 THEN 4
            ELSE 5
        END AS band_order
    FROM delivered_orders
)
SELECT
    delivery_timing_band,
    band_order,
    COUNT(*) AS delivered_orders,
    ROUND(AVG(delivery_delay_days)::NUMERIC, 2) AS average_delay_days,
    ROUND(AVG(average_review_score)::NUMERIC, 2) AS average_review_score,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE average_review_score <= 2)
        / NULLIF(COUNT(*) FILTER (WHERE average_review_score IS NOT NULL), 0),
        2
    ) AS low_review_rate_pct
FROM banded
GROUP BY delivery_timing_band, band_order
ORDER BY band_order;

-- name: customer_purchase_frequency
-- grain: One row per delivered-order frequency band, using customer_unique_id.
WITH customer_orders AS (
    SELECT
        c.customer_unique_id,
        COUNT(DISTINCT o.order_id) AS delivered_orders,
        MIN(o.order_purchase_timestamp)::DATE AS first_order_date,
        MAX(o.order_purchase_timestamp)::DATE AS last_order_date
    FROM commerceiq.orders AS o
    JOIN commerceiq.customers AS c ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id
),
banded AS (
    SELECT
        *,
        CASE
            WHEN delivered_orders = 1 THEN '1 order'
            WHEN delivered_orders = 2 THEN '2 orders'
            WHEN delivered_orders = 3 THEN '3 orders'
            ELSE '4+ orders'
        END AS frequency_band,
        LEAST(delivered_orders, 4) AS band_order
    FROM customer_orders
)
SELECT
    frequency_band,
    band_order,
    COUNT(*) AS customers,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS customer_share_pct,
    ROUND(AVG(delivered_orders)::NUMERIC, 2) AS average_delivered_orders
FROM banded
GROUP BY frequency_band, band_order
ORDER BY band_order;

-- name: monthly_customer_cohorts
-- grain: One row per first-delivered-order cohort and activity month number.
WITH customer_orders AS (
    SELECT
        c.customer_unique_id,
        DATE_TRUNC('month', o.order_purchase_timestamp)::DATE AS order_month
    FROM commerceiq.orders AS o
    JOIN commerceiq.customers AS c ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_unique_id, DATE_TRUNC('month', o.order_purchase_timestamp)::DATE
),
cohorted AS (
    SELECT
        customer_unique_id,
        order_month,
        MIN(order_month) OVER (PARTITION BY customer_unique_id) AS cohort_month
    FROM customer_orders
),
cohort_activity AS (
    SELECT
        cohort_month,
        (
            (EXTRACT(YEAR FROM order_month) - EXTRACT(YEAR FROM cohort_month)) * 12
            + EXTRACT(MONTH FROM order_month) - EXTRACT(MONTH FROM cohort_month)
        )::INTEGER AS month_number,
        COUNT(DISTINCT customer_unique_id) AS active_customers
    FROM cohorted
    GROUP BY cohort_month, month_number
),
cohort_sizes AS (
    SELECT cohort_month, active_customers AS cohort_size
    FROM cohort_activity
    WHERE month_number = 0
)
SELECT
    a.cohort_month,
    a.month_number,
    s.cohort_size,
    a.active_customers,
    ROUND(100.0 * a.active_customers / NULLIF(s.cohort_size, 0), 2)
        AS retention_rate_pct
FROM cohort_activity AS a
JOIN cohort_sizes AS s USING (cohort_month)
ORDER BY a.cohort_month, a.month_number;

-- name: seller_scorecard
-- grain: One row per seller with at least one delivered order.
WITH review_by_order AS (
    SELECT order_id, AVG(review_score)::NUMERIC AS average_review_score
    FROM commerceiq.order_reviews
    GROUP BY order_id
),
seller_order AS (
    SELECT
        i.seller_id,
        i.order_id,
        SUM(i.price)::NUMERIC AS item_revenue,
        SUM(i.freight_value)::NUMERIC AS freight_revenue,
        BOOL_AND(
            o.order_delivered_customer_date IS NOT NULL
            AND o.order_estimated_delivery_date IS NOT NULL
            AND o.order_delivered_customer_date::DATE <= o.order_estimated_delivery_date::DATE
        ) AS delivered_on_time,
        r.average_review_score
    FROM commerceiq.order_items AS i
    JOIN commerceiq.orders AS o ON o.order_id = i.order_id
    LEFT JOIN review_by_order AS r ON r.order_id = i.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY i.seller_id, i.order_id, r.average_review_score
)
SELECT
    so.seller_id,
    s.seller_state,
    COUNT(*) AS delivered_orders,
    ROUND(SUM(so.item_revenue), 2) AS delivered_gmv,
    ROUND(SUM(so.item_revenue) / NULLIF(COUNT(*), 0), 2)
        AS average_order_revenue,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE so.delivered_on_time)
        / NULLIF(COUNT(*), 0),
        2
    ) AS on_time_delivery_rate_pct,
    ROUND(AVG(so.average_review_score)::NUMERIC, 2) AS average_review_score,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE so.average_review_score <= 2)
        / NULLIF(COUNT(*) FILTER (WHERE so.average_review_score IS NOT NULL), 0),
        2
    ) AS low_review_rate_pct
FROM seller_order AS so
JOIN commerceiq.sellers AS s ON s.seller_id = so.seller_id
GROUP BY so.seller_id, s.seller_state
ORDER BY delivered_gmv DESC, so.seller_id;

-- CommerceIQ foundational KPI queries.
-- Each query begins with a machine-readable name used by the analytics runner.

-- name: executive_summary
-- grain: One row for the complete observed dataset.
WITH review_by_order AS (
    SELECT order_id, AVG(review_score)::NUMERIC AS average_review_score
    FROM commerceiq.order_reviews
    GROUP BY order_id
),
order_value AS (
    SELECT
        order_id,
        SUM(price)::NUMERIC AS item_revenue,
        SUM(freight_value)::NUMERIC AS freight_revenue
    FROM commerceiq.order_items
    GROUP BY order_id
),
order_metrics AS (
    SELECT
        o.order_id,
        c.customer_unique_id,
        o.order_status,
        o.order_purchase_timestamp,
        o.order_delivered_customer_date,
        o.order_estimated_delivery_date,
        COALESCE(v.item_revenue, 0)::NUMERIC AS item_revenue,
        r.average_review_score
    FROM commerceiq.orders AS o
    JOIN commerceiq.customers AS c ON c.customer_id = o.customer_id
    LEFT JOIN order_value AS v ON v.order_id = o.order_id
    LEFT JOIN review_by_order AS r ON r.order_id = o.order_id
),
delivered_customer_orders AS (
    SELECT customer_unique_id, COUNT(DISTINCT order_id) AS delivered_orders
    FROM order_metrics
    WHERE order_status = 'delivered'
    GROUP BY customer_unique_id
),
customer_summary AS (
    SELECT
        COUNT(*) AS delivered_customers,
        COUNT(*) FILTER (WHERE delivered_orders >= 2) AS repeat_customers
    FROM delivered_customer_orders
),
seller_summary AS (
    SELECT COUNT(DISTINCT i.seller_id) AS active_sellers
    FROM commerceiq.order_items AS i
    JOIN commerceiq.orders AS o ON o.order_id = i.order_id
    WHERE o.order_status = 'delivered'
)
SELECT
    MIN(order_purchase_timestamp)::DATE AS first_order_date,
    MAX(order_purchase_timestamp)::DATE AS last_order_date,
    COUNT(*) AS total_orders,
    COUNT(*) FILTER (WHERE order_status = 'delivered') AS delivered_orders,
    COUNT(DISTINCT customer_unique_id) AS unique_customers,
    seller_summary.active_sellers,
    ROUND(
        SUM(item_revenue) FILTER (WHERE order_status = 'delivered'),
        2
    ) AS delivered_gmv,
    ROUND(
        SUM(item_revenue) FILTER (WHERE order_status = 'delivered')
        / NULLIF(COUNT(*) FILTER (WHERE order_status = 'delivered'), 0),
        2
    ) AS delivered_average_order_value,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE order_status = 'canceled')
        / NULLIF(COUNT(*), 0),
        2
    ) AS cancellation_rate_pct,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE order_status = 'delivered'
              AND order_delivered_customer_date IS NOT NULL
              AND order_estimated_delivery_date IS NOT NULL
              AND order_delivered_customer_date::DATE <= order_estimated_delivery_date::DATE
        )
        / NULLIF(COUNT(*) FILTER (
            WHERE order_status = 'delivered'
              AND order_delivered_customer_date IS NOT NULL
              AND order_estimated_delivery_date IS NOT NULL
        ), 0),
        2
    ) AS on_time_delivery_rate_pct,
    ROUND(
        AVG(
            EXTRACT(EPOCH FROM (order_delivered_customer_date - order_purchase_timestamp))
            / 86400.0
        ) FILTER (
            WHERE order_status = 'delivered'
              AND order_delivered_customer_date IS NOT NULL
        )::NUMERIC,
        2
    ) AS average_delivery_days,
    ROUND(AVG(average_review_score)::NUMERIC, 2) AS average_review_score,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE average_review_score <= 2)
        / NULLIF(COUNT(*) FILTER (WHERE average_review_score IS NOT NULL), 0),
        2
    ) AS low_review_rate_pct,
    ROUND(
        100.0 * customer_summary.repeat_customers
        / NULLIF(customer_summary.delivered_customers, 0),
        2
    ) AS repeat_customer_rate_pct
FROM order_metrics
CROSS JOIN customer_summary
CROSS JOIN seller_summary
GROUP BY
    customer_summary.repeat_customers,
    customer_summary.delivered_customers,
    seller_summary.active_sellers;

-- name: monthly_performance
-- grain: One row per purchase month.
WITH review_by_order AS (
    SELECT order_id, AVG(review_score)::NUMERIC AS average_review_score
    FROM commerceiq.order_reviews
    GROUP BY order_id
),
order_value AS (
    SELECT order_id, SUM(price)::NUMERIC AS item_revenue
    FROM commerceiq.order_items
    GROUP BY order_id
),
order_metrics AS (
    SELECT
        o.order_id,
        DATE_TRUNC('month', o.order_purchase_timestamp)::DATE AS order_month,
        o.order_status,
        o.order_purchase_timestamp,
        o.order_delivered_customer_date,
        o.order_estimated_delivery_date,
        COALESCE(v.item_revenue, 0)::NUMERIC AS item_revenue,
        r.average_review_score
    FROM commerceiq.orders AS o
    LEFT JOIN order_value AS v ON v.order_id = o.order_id
    LEFT JOIN review_by_order AS r ON r.order_id = o.order_id
)
SELECT
    order_month,
    COUNT(*) AS total_orders,
    COUNT(*) FILTER (WHERE order_status = 'delivered') AS delivered_orders,
    COUNT(*) FILTER (WHERE order_status = 'canceled') AS canceled_orders,
    ROUND(
        SUM(item_revenue) FILTER (WHERE order_status = 'delivered'),
        2
    ) AS delivered_gmv,
    ROUND(
        SUM(item_revenue) FILTER (WHERE order_status = 'delivered')
        / NULLIF(COUNT(*) FILTER (WHERE order_status = 'delivered'), 0),
        2
    ) AS delivered_average_order_value,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE order_status = 'canceled')
        / NULLIF(COUNT(*), 0),
        2
    ) AS cancellation_rate_pct,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE order_status = 'delivered'
              AND order_delivered_customer_date::DATE <= order_estimated_delivery_date::DATE
        )
        / NULLIF(COUNT(*) FILTER (
            WHERE order_status = 'delivered'
              AND order_delivered_customer_date IS NOT NULL
              AND order_estimated_delivery_date IS NOT NULL
        ), 0),
        2
    ) AS on_time_delivery_rate_pct,
    ROUND(
        AVG(
            EXTRACT(EPOCH FROM (order_delivered_customer_date - order_purchase_timestamp))
            / 86400.0
        ) FILTER (
            WHERE order_status = 'delivered'
              AND order_delivered_customer_date IS NOT NULL
        )::NUMERIC,
        2
    ) AS average_delivery_days,
    ROUND(AVG(average_review_score)::NUMERIC, 2) AS average_review_score
FROM order_metrics
GROUP BY order_month
ORDER BY order_month;

-- name: category_performance
-- grain: One row per English product category for delivered orders.
WITH review_by_order AS (
    SELECT order_id, AVG(review_score)::NUMERIC AS average_review_score
    FROM commerceiq.order_reviews
    GROUP BY order_id
),
category_order AS (
    SELECT
        p.product_category_name_english AS category_name,
        i.order_id,
        COUNT(*) AS item_count,
        SUM(i.price)::NUMERIC AS item_revenue,
        SUM(i.freight_value)::NUMERIC AS freight_revenue
    FROM commerceiq.order_items AS i
    JOIN commerceiq.orders AS o ON o.order_id = i.order_id
    JOIN commerceiq.products AS p ON p.product_id = i.product_id
    WHERE o.order_status = 'delivered'
    GROUP BY p.product_category_name_english, i.order_id
)
SELECT
    category_name,
    COUNT(*) AS delivered_orders,
    SUM(item_count)::BIGINT AS items_sold,
    ROUND(SUM(item_revenue), 2) AS delivered_gmv,
    ROUND(SUM(freight_revenue), 2) AS freight_revenue,
    ROUND(SUM(item_revenue) / NULLIF(SUM(item_count), 0), 2) AS average_item_price,
    ROUND(AVG(r.average_review_score)::NUMERIC, 2) AS average_review_score
FROM category_order AS c
LEFT JOIN review_by_order AS r ON r.order_id = c.order_id
GROUP BY category_name
ORDER BY delivered_gmv DESC, category_name;

-- name: state_performance
-- grain: One row per customer state.
WITH order_value AS (
    SELECT order_id, SUM(price)::NUMERIC AS item_revenue
    FROM commerceiq.order_items
    GROUP BY order_id
),
review_by_order AS (
    SELECT order_id, AVG(review_score)::NUMERIC AS average_review_score
    FROM commerceiq.order_reviews
    GROUP BY order_id
)
SELECT
    c.customer_state AS customer_state,
    COUNT(*) AS total_orders,
    COUNT(*) FILTER (WHERE o.order_status = 'delivered') AS delivered_orders,
    ROUND(
        SUM(v.item_revenue) FILTER (WHERE o.order_status = 'delivered'),
        2
    ) AS delivered_gmv,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE o.order_status = 'canceled')
        / NULLIF(COUNT(*), 0),
        2
    ) AS cancellation_rate_pct,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE o.order_status = 'delivered'
              AND o.order_delivered_customer_date::DATE <= o.order_estimated_delivery_date::DATE
        )
        / NULLIF(COUNT(*) FILTER (
            WHERE o.order_status = 'delivered'
              AND o.order_delivered_customer_date IS NOT NULL
              AND o.order_estimated_delivery_date IS NOT NULL
        ), 0),
        2
    ) AS on_time_delivery_rate_pct,
    ROUND(AVG(r.average_review_score)::NUMERIC, 2) AS average_review_score
FROM commerceiq.orders AS o
JOIN commerceiq.customers AS c ON c.customer_id = o.customer_id
LEFT JOIN order_value AS v ON v.order_id = o.order_id
LEFT JOIN review_by_order AS r ON r.order_id = o.order_id
GROUP BY c.customer_state
ORDER BY delivered_gmv DESC, c.customer_state;

-- name: payment_method_performance
-- grain: One row per payment type; orders can appear in more than one type.
SELECT
    payment_type,
    COUNT(*) AS payment_records,
    COUNT(DISTINCT order_id) AS orders_using_method,
    ROUND(SUM(payment_value), 2) AS payment_value,
    ROUND(AVG(payment_value), 2) AS average_payment_record_value,
    ROUND(AVG(payment_installments)::NUMERIC, 2) AS average_installments,
    ROUND(
        100.0 * SUM(payment_value) / NULLIF(SUM(SUM(payment_value)) OVER (), 0),
        2
    ) AS payment_value_share_pct
FROM commerceiq.order_payments
GROUP BY payment_type
ORDER BY payment_value DESC, payment_type;

-- name: order_status_distribution
-- grain: One row per order status.
SELECT
    order_status,
    COUNT(*) AS order_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS order_share_pct
FROM commerceiq.orders
GROUP BY order_status
ORDER BY order_count DESC, order_status;

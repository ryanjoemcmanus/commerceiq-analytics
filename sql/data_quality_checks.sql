-- CommerceIQ database-level integrity checks.
-- A healthy load returns zero violations for every check except explicitly
-- retained source-quality flags, which remain visible for analysis.

WITH checks AS (
    SELECT 'customers_duplicate_pk' AS check_name, COUNT(*)::BIGINT AS violation_count
    FROM (
        SELECT customer_id FROM commerceiq.customers
        GROUP BY customer_id HAVING COUNT(*) > 1
    ) AS duplicates

    UNION ALL
    SELECT 'orders_without_customer', COUNT(*)
    FROM commerceiq.orders AS o
    LEFT JOIN commerceiq.customers AS c ON c.customer_id = o.customer_id
    WHERE c.customer_id IS NULL

    UNION ALL
    SELECT 'order_items_without_order', COUNT(*)
    FROM commerceiq.order_items AS i
    LEFT JOIN commerceiq.orders AS o ON o.order_id = i.order_id
    WHERE o.order_id IS NULL

    UNION ALL
    SELECT 'order_items_without_product', COUNT(*)
    FROM commerceiq.order_items AS i
    LEFT JOIN commerceiq.products AS p ON p.product_id = i.product_id
    WHERE p.product_id IS NULL

    UNION ALL
    SELECT 'order_items_without_seller', COUNT(*)
    FROM commerceiq.order_items AS i
    LEFT JOIN commerceiq.sellers AS s ON s.seller_id = i.seller_id
    WHERE s.seller_id IS NULL

    UNION ALL
    SELECT 'payments_without_order', COUNT(*)
    FROM commerceiq.order_payments AS p
    LEFT JOIN commerceiq.orders AS o ON o.order_id = p.order_id
    WHERE o.order_id IS NULL

    UNION ALL
    SELECT 'reviews_without_order', COUNT(*)
    FROM commerceiq.order_reviews AS r
    LEFT JOIN commerceiq.orders AS o ON o.order_id = r.order_id
    WHERE o.order_id IS NULL

    UNION ALL
    SELECT 'products_without_category_dimension', COUNT(*)
    FROM commerceiq.products AS p
    LEFT JOIN commerceiq.product_categories AS c
        ON c.product_category_name = p.product_category_name
    WHERE p.product_category_name IS NOT NULL
      AND c.product_category_name IS NULL

    UNION ALL
    SELECT 'negative_item_amounts', COUNT(*)
    FROM commerceiq.order_items
    WHERE price < 0 OR freight_value < 0

    UNION ALL
    SELECT 'negative_payment_values', COUNT(*)
    FROM commerceiq.order_payments
    WHERE payment_value < 0 OR payment_installments < 0

    UNION ALL
    SELECT 'invalid_review_scores', COUNT(*)
    FROM commerceiq.order_reviews
    WHERE review_score NOT BETWEEN 1 AND 5

    UNION ALL
    SELECT 'retained_order_timestamp_sequence_flags', COUNT(*)
    FROM commerceiq.orders
    WHERE dq_has_timestamp_sequence_issue

    UNION ALL
    SELECT 'retained_missing_product_categories', COUNT(*)
    FROM commerceiq.products
    WHERE dq_category_missing

    UNION ALL
    SELECT 'retained_fallback_category_translations', COUNT(*)
    FROM commerceiq.product_categories
    WHERE dq_translation_missing
)
SELECT
    check_name,
    violation_count,
    CASE
        WHEN check_name LIKE 'retained_%' THEN 'informational'
        WHEN violation_count = 0 THEN 'passed'
        ELSE 'failed'
    END AS status
FROM checks
ORDER BY status DESC, check_name;


-- CommerceIQ PostgreSQL schema
-- Source timestamps are stored without a timezone because the Olist files do
-- not provide timezone offsets. Raw source files remain outside the database.

CREATE SCHEMA IF NOT EXISTS commerceiq;

CREATE TABLE IF NOT EXISTS commerceiq.customers (
    customer_id VARCHAR(32) PRIMARY KEY,
    customer_unique_id VARCHAR(32) NOT NULL,
    customer_zip_code_prefix INTEGER NOT NULL,
    customer_city TEXT NOT NULL,
    customer_state CHAR(2) NOT NULL
);

CREATE TABLE IF NOT EXISTS commerceiq.product_categories (
    product_category_name TEXT PRIMARY KEY,
    product_category_name_english TEXT NOT NULL,
    dq_translation_missing BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS commerceiq.products (
    product_id VARCHAR(32) PRIMARY KEY,
    product_category_name TEXT NULL,
    product_name_length INTEGER NULL,
    product_description_length INTEGER NULL,
    product_photos_qty INTEGER NULL,
    product_weight_g INTEGER NULL,
    product_length_cm INTEGER NULL,
    product_height_cm INTEGER NULL,
    product_width_cm INTEGER NULL,
    dq_category_missing BOOLEAN NOT NULL,
    dq_category_translation_missing BOOLEAN NOT NULL,
    product_category_name_english TEXT NOT NULL,
    CONSTRAINT fk_products_category
        FOREIGN KEY (product_category_name)
        REFERENCES commerceiq.product_categories (product_category_name),
    CONSTRAINT ck_products_nonnegative_dimensions CHECK (
        (product_weight_g IS NULL OR product_weight_g >= 0)
        AND (product_length_cm IS NULL OR product_length_cm >= 0)
        AND (product_height_cm IS NULL OR product_height_cm >= 0)
        AND (product_width_cm IS NULL OR product_width_cm >= 0)
        AND (product_photos_qty IS NULL OR product_photos_qty >= 0)
    )
);

CREATE TABLE IF NOT EXISTS commerceiq.sellers (
    seller_id VARCHAR(32) PRIMARY KEY,
    seller_zip_code_prefix INTEGER NOT NULL,
    seller_city TEXT NOT NULL,
    seller_state CHAR(2) NOT NULL
);

CREATE TABLE IF NOT EXISTS commerceiq.geolocation_lookup (
    zip_code_prefix INTEGER PRIMARY KEY,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    unique_observation_count INTEGER NOT NULL,
    city_variant_count INTEGER NOT NULL,
    state_variant_count INTEGER NOT NULL,
    city TEXT NOT NULL,
    state CHAR(2) NOT NULL,
    source_observation_count INTEGER NOT NULL,
    dq_multiple_state_codes BOOLEAN NOT NULL,
    CONSTRAINT ck_geolocation_lookup_coordinates CHECK (
        latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180
    )
);

CREATE TABLE IF NOT EXISTS commerceiq.geolocation_observations (
    geolocation_id BIGSERIAL PRIMARY KEY,
    geolocation_zip_code_prefix INTEGER NOT NULL,
    geolocation_lat DOUBLE PRECISION NOT NULL,
    geolocation_lng DOUBLE PRECISION NOT NULL,
    geolocation_city TEXT NOT NULL,
    geolocation_state CHAR(2) NOT NULL,
    CONSTRAINT uq_geolocation_observation UNIQUE (
        geolocation_zip_code_prefix,
        geolocation_lat,
        geolocation_lng,
        geolocation_city,
        geolocation_state
    ),
    CONSTRAINT ck_geolocation_observation_coordinates CHECK (
        geolocation_lat BETWEEN -90 AND 90
        AND geolocation_lng BETWEEN -180 AND 180
    )
);

CREATE TABLE IF NOT EXISTS commerceiq.orders (
    order_id VARCHAR(32) PRIMARY KEY,
    customer_id VARCHAR(32) NOT NULL,
    order_status TEXT NOT NULL,
    order_purchase_timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    order_approved_at TIMESTAMP WITHOUT TIME ZONE NULL,
    order_delivered_carrier_date TIMESTAMP WITHOUT TIME ZONE NULL,
    order_delivered_customer_date TIMESTAMP WITHOUT TIME ZONE NULL,
    order_estimated_delivery_date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    dq_invalid_order_purchase_timestamp BOOLEAN NOT NULL,
    dq_invalid_order_approved_at BOOLEAN NOT NULL,
    dq_invalid_order_delivered_carrier_date BOOLEAN NOT NULL,
    dq_invalid_order_delivered_customer_date BOOLEAN NOT NULL,
    dq_invalid_order_estimated_delivery_date BOOLEAN NOT NULL,
    dq_purchase_after_carrier_handoff BOOLEAN NOT NULL,
    dq_approval_after_carrier_handoff BOOLEAN NOT NULL,
    dq_carrier_handoff_after_customer_delivery BOOLEAN NOT NULL,
    dq_has_timestamp_sequence_issue BOOLEAN NOT NULL,
    CONSTRAINT fk_orders_customer
        FOREIGN KEY (customer_id) REFERENCES commerceiq.customers (customer_id),
    CONSTRAINT ck_orders_status CHECK (
        order_status IN (
            'approved', 'canceled', 'created', 'delivered',
            'invoiced', 'processing', 'shipped', 'unavailable'
        )
    )
);

CREATE TABLE IF NOT EXISTS commerceiq.order_items (
    order_id VARCHAR(32) NOT NULL,
    order_item_id INTEGER NOT NULL,
    product_id VARCHAR(32) NOT NULL,
    seller_id VARCHAR(32) NOT NULL,
    shipping_limit_date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    price NUMERIC(14, 2) NOT NULL,
    freight_value NUMERIC(14, 2) NOT NULL,
    dq_invalid_shipping_limit_date BOOLEAN NOT NULL,
    dq_negative_price BOOLEAN NOT NULL,
    dq_negative_freight_value BOOLEAN NOT NULL,
    PRIMARY KEY (order_id, order_item_id),
    CONSTRAINT fk_order_items_order
        FOREIGN KEY (order_id) REFERENCES commerceiq.orders (order_id),
    CONSTRAINT fk_order_items_product
        FOREIGN KEY (product_id) REFERENCES commerceiq.products (product_id),
    CONSTRAINT fk_order_items_seller
        FOREIGN KEY (seller_id) REFERENCES commerceiq.sellers (seller_id),
    CONSTRAINT ck_order_items_amounts CHECK (price >= 0 AND freight_value >= 0)
);

CREATE TABLE IF NOT EXISTS commerceiq.order_payments (
    order_id VARCHAR(32) NOT NULL,
    payment_sequential INTEGER NOT NULL,
    payment_type TEXT NOT NULL,
    payment_installments INTEGER NOT NULL,
    payment_value NUMERIC(14, 2) NOT NULL,
    dq_negative_payment_value BOOLEAN NOT NULL,
    dq_negative_payment_installments BOOLEAN NOT NULL,
    PRIMARY KEY (order_id, payment_sequential),
    CONSTRAINT fk_order_payments_order
        FOREIGN KEY (order_id) REFERENCES commerceiq.orders (order_id),
    CONSTRAINT ck_order_payments_values CHECK (
        payment_value >= 0 AND payment_installments >= 0
    )
);

CREATE TABLE IF NOT EXISTS commerceiq.order_reviews (
    review_id VARCHAR(32) NOT NULL,
    order_id VARCHAR(32) NOT NULL,
    review_score SMALLINT NOT NULL,
    review_comment_title TEXT NULL,
    review_comment_message TEXT NULL,
    review_creation_date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    review_answer_timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    dq_invalid_review_creation_date BOOLEAN NOT NULL,
    dq_invalid_review_answer_timestamp BOOLEAN NOT NULL,
    dq_review_score_out_of_range BOOLEAN NOT NULL,
    PRIMARY KEY (review_id, order_id),
    CONSTRAINT fk_order_reviews_order
        FOREIGN KEY (order_id) REFERENCES commerceiq.orders (order_id),
    CONSTRAINT ck_order_reviews_score CHECK (review_score BETWEEN 1 AND 5)
);

CREATE INDEX IF NOT EXISTS idx_customers_unique_id
    ON commerceiq.customers (customer_unique_id);
CREATE INDEX IF NOT EXISTS idx_orders_customer_id
    ON commerceiq.orders (customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_purchase_timestamp
    ON commerceiq.orders (order_purchase_timestamp);
CREATE INDEX IF NOT EXISTS idx_orders_status
    ON commerceiq.orders (order_status);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id
    ON commerceiq.order_items (product_id);
CREATE INDEX IF NOT EXISTS idx_order_items_seller_id
    ON commerceiq.order_items (seller_id);
CREATE INDEX IF NOT EXISTS idx_products_category
    ON commerceiq.products (product_category_name);
CREATE INDEX IF NOT EXISTS idx_geolocation_observations_zip
    ON commerceiq.geolocation_observations (geolocation_zip_code_prefix);


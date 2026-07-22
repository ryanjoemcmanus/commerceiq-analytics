"""Declarative source-table contracts for the public Olist dataset."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TableContract:
    """Expected source schema, grain, and key for one CSV table."""

    file_name: str
    grain: str
    required_columns: tuple[str, ...]
    primary_key: tuple[str, ...] = ()


@dataclass(frozen=True)
class ForeignKeyContract:
    """Expected relationship between a child and parent source table."""

    name: str
    child_file: str
    child_column: str
    parent_file: str
    parent_column: str
    nullable: bool = False
    strict: bool = True


@dataclass(frozen=True)
class TimestampOrderContract:
    """Expected chronological ordering for two timestamp columns."""

    name: str
    file_name: str
    earlier_column: str
    later_column: str


TABLE_CONTRACTS = {
    "olist_customers_dataset.csv": TableContract(
        file_name="olist_customers_dataset.csv",
        grain="One marketplace customer record per customer_id",
        primary_key=("customer_id",),
        required_columns=(
            "customer_id",
            "customer_unique_id",
            "customer_zip_code_prefix",
            "customer_city",
            "customer_state",
        ),
    ),
    "olist_geolocation_dataset.csv": TableContract(
        file_name="olist_geolocation_dataset.csv",
        grain="One geolocation observation; multiple observations may share a ZIP prefix",
        required_columns=(
            "geolocation_zip_code_prefix",
            "geolocation_lat",
            "geolocation_lng",
            "geolocation_city",
            "geolocation_state",
        ),
    ),
    "olist_orders_dataset.csv": TableContract(
        file_name="olist_orders_dataset.csv",
        grain="One order per order_id",
        primary_key=("order_id",),
        required_columns=(
            "order_id",
            "customer_id",
            "order_status",
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ),
    ),
    "olist_order_items_dataset.csv": TableContract(
        file_name="olist_order_items_dataset.csv",
        grain="One item sequence within an order",
        primary_key=("order_id", "order_item_id"),
        required_columns=(
            "order_id",
            "order_item_id",
            "product_id",
            "seller_id",
            "shipping_limit_date",
            "price",
            "freight_value",
        ),
    ),
    "olist_order_payments_dataset.csv": TableContract(
        file_name="olist_order_payments_dataset.csv",
        grain="One payment sequence within an order",
        primary_key=("order_id", "payment_sequential"),
        required_columns=(
            "order_id",
            "payment_sequential",
            "payment_type",
            "payment_installments",
            "payment_value",
        ),
    ),
    "olist_order_reviews_dataset.csv": TableContract(
        file_name="olist_order_reviews_dataset.csv",
        grain="One review-order association",
        primary_key=("review_id", "order_id"),
        required_columns=(
            "review_id",
            "order_id",
            "review_score",
            "review_comment_title",
            "review_comment_message",
            "review_creation_date",
            "review_answer_timestamp",
        ),
    ),
    "olist_products_dataset.csv": TableContract(
        file_name="olist_products_dataset.csv",
        grain="One product per product_id",
        primary_key=("product_id",),
        required_columns=(
            "product_id",
            "product_category_name",
            "product_name_lenght",
            "product_description_lenght",
            "product_photos_qty",
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm",
        ),
    ),
    "olist_sellers_dataset.csv": TableContract(
        file_name="olist_sellers_dataset.csv",
        grain="One seller per seller_id",
        primary_key=("seller_id",),
        required_columns=(
            "seller_id",
            "seller_zip_code_prefix",
            "seller_city",
            "seller_state",
        ),
    ),
    "product_category_name_translation.csv": TableContract(
        file_name="product_category_name_translation.csv",
        grain="One Portuguese product category name",
        primary_key=("product_category_name",),
        required_columns=(
            "product_category_name",
            "product_category_name_english",
        ),
    ),
}


FOREIGN_KEY_CONTRACTS = (
    ForeignKeyContract(
        "orders_to_customers",
        "olist_orders_dataset.csv",
        "customer_id",
        "olist_customers_dataset.csv",
        "customer_id",
    ),
    ForeignKeyContract(
        "items_to_orders",
        "olist_order_items_dataset.csv",
        "order_id",
        "olist_orders_dataset.csv",
        "order_id",
    ),
    ForeignKeyContract(
        "items_to_products",
        "olist_order_items_dataset.csv",
        "product_id",
        "olist_products_dataset.csv",
        "product_id",
    ),
    ForeignKeyContract(
        "items_to_sellers",
        "olist_order_items_dataset.csv",
        "seller_id",
        "olist_sellers_dataset.csv",
        "seller_id",
    ),
    ForeignKeyContract(
        "payments_to_orders",
        "olist_order_payments_dataset.csv",
        "order_id",
        "olist_orders_dataset.csv",
        "order_id",
    ),
    ForeignKeyContract(
        "reviews_to_orders",
        "olist_order_reviews_dataset.csv",
        "order_id",
        "olist_orders_dataset.csv",
        "order_id",
    ),
    ForeignKeyContract(
        "products_to_category_translation",
        "olist_products_dataset.csv",
        "product_category_name",
        "product_category_name_translation.csv",
        "product_category_name",
        nullable=True,
        strict=False,
    ),
)


TIMESTAMP_ORDER_CONTRACTS = (
    TimestampOrderContract(
        "purchase_before_approval",
        "olist_orders_dataset.csv",
        "order_purchase_timestamp",
        "order_approved_at",
    ),
    TimestampOrderContract(
        "purchase_before_carrier_handoff",
        "olist_orders_dataset.csv",
        "order_purchase_timestamp",
        "order_delivered_carrier_date",
    ),
    TimestampOrderContract(
        "purchase_before_customer_delivery",
        "olist_orders_dataset.csv",
        "order_purchase_timestamp",
        "order_delivered_customer_date",
    ),
    TimestampOrderContract(
        "purchase_before_estimated_delivery",
        "olist_orders_dataset.csv",
        "order_purchase_timestamp",
        "order_estimated_delivery_date",
    ),
    TimestampOrderContract(
        "approval_before_carrier_handoff",
        "olist_orders_dataset.csv",
        "order_approved_at",
        "order_delivered_carrier_date",
    ),
    TimestampOrderContract(
        "carrier_handoff_before_customer_delivery",
        "olist_orders_dataset.csv",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
    ),
    TimestampOrderContract(
        "review_creation_before_answer",
        "olist_order_reviews_dataset.csv",
        "review_creation_date",
        "review_answer_timestamp",
    ),
)


ALLOWED_ORDER_STATUSES = frozenset(
    {
        "approved",
        "canceled",
        "created",
        "delivered",
        "invoiced",
        "processing",
        "shipped",
        "unavailable",
    }
)


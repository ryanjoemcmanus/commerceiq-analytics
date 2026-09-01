"""Transactional PostgreSQL loading utilities for CommerceIQ."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sqlalchemy import Connection, Engine, create_engine, text

from src.config import DatabaseSettings

DATABASE_SCHEMA = "commerceiq"


@dataclass(frozen=True)
class TableLoadSpec:
    """Mapping and type preparation for one processed CSV table."""

    file_name: str
    table_name: str
    required_columns: tuple[str, ...]
    timestamp_columns: tuple[str, ...] = ()
    integer_columns: tuple[str, ...] = ()


TABLE_LOAD_SPECS = (
    TableLoadSpec(
        "product_category_name_translation.csv",
        "product_categories",
        (
            "product_category_name",
            "product_category_name_english",
            "dq_translation_missing",
        ),
    ),
    TableLoadSpec(
        "olist_customers_dataset.csv",
        "customers",
        (
            "customer_id",
            "customer_unique_id",
            "customer_zip_code_prefix",
            "customer_city",
            "customer_state",
        ),
        integer_columns=("customer_zip_code_prefix",),
    ),
    TableLoadSpec(
        "olist_products_dataset.csv",
        "products",
        (
            "product_id",
            "product_category_name",
            "product_name_length",
            "product_description_length",
            "product_photos_qty",
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm",
            "dq_category_missing",
            "dq_category_translation_missing",
            "product_category_name_english",
        ),
        integer_columns=(
            "product_name_length",
            "product_description_length",
            "product_photos_qty",
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm",
        ),
    ),
    TableLoadSpec(
        "olist_sellers_dataset.csv",
        "sellers",
        ("seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"),
        integer_columns=("seller_zip_code_prefix",),
    ),
    TableLoadSpec(
        "geolocation_lookup.csv",
        "geolocation_lookup",
        (
            "zip_code_prefix",
            "latitude",
            "longitude",
            "unique_observation_count",
            "city_variant_count",
            "state_variant_count",
            "city",
            "state",
            "source_observation_count",
            "dq_multiple_state_codes",
        ),
        integer_columns=(
            "zip_code_prefix",
            "unique_observation_count",
            "city_variant_count",
            "state_variant_count",
            "source_observation_count",
        ),
    ),
    TableLoadSpec(
        "olist_geolocation_dataset.csv",
        "geolocation_observations",
        (
            "geolocation_zip_code_prefix",
            "geolocation_lat",
            "geolocation_lng",
            "geolocation_city",
            "geolocation_state",
        ),
        integer_columns=("geolocation_zip_code_prefix",),
    ),
    TableLoadSpec(
        "olist_orders_dataset.csv",
        "orders",
        (
            "order_id",
            "customer_id",
            "order_status",
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
            "dq_invalid_order_purchase_timestamp",
            "dq_invalid_order_approved_at",
            "dq_invalid_order_delivered_carrier_date",
            "dq_invalid_order_delivered_customer_date",
            "dq_invalid_order_estimated_delivery_date",
            "dq_purchase_after_carrier_handoff",
            "dq_approval_after_carrier_handoff",
            "dq_carrier_handoff_after_customer_delivery",
            "dq_has_timestamp_sequence_issue",
        ),
        timestamp_columns=(
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ),
    ),
    TableLoadSpec(
        "olist_order_items_dataset.csv",
        "order_items",
        (
            "order_id",
            "order_item_id",
            "product_id",
            "seller_id",
            "shipping_limit_date",
            "price",
            "freight_value",
            "dq_invalid_shipping_limit_date",
            "dq_negative_price",
            "dq_negative_freight_value",
        ),
        timestamp_columns=("shipping_limit_date",),
        integer_columns=("order_item_id",),
    ),
    TableLoadSpec(
        "olist_order_payments_dataset.csv",
        "order_payments",
        (
            "order_id",
            "payment_sequential",
            "payment_type",
            "payment_installments",
            "payment_value",
            "dq_negative_payment_value",
            "dq_negative_payment_installments",
        ),
        integer_columns=("payment_sequential", "payment_installments"),
    ),
    TableLoadSpec(
        "olist_order_reviews_dataset.csv",
        "order_reviews",
        (
            "review_id",
            "order_id",
            "review_score",
            "review_comment_title",
            "review_comment_message",
            "review_creation_date",
            "review_answer_timestamp",
            "dq_invalid_review_creation_date",
            "dq_invalid_review_answer_timestamp",
            "dq_review_score_out_of_range",
        ),
        timestamp_columns=("review_creation_date", "review_answer_timestamp"),
        integer_columns=("review_score",),
    ),
)

NOT_NULL_COLUMNS = {
    "product_categories": (
        "product_category_name",
        "product_category_name_english",
        "dq_translation_missing",
    ),
    "customers": (
        "customer_id",
        "customer_unique_id",
        "customer_zip_code_prefix",
        "customer_city",
        "customer_state",
    ),
    "products": (
        "product_id",
        "dq_category_missing",
        "dq_category_translation_missing",
        "product_category_name_english",
    ),
    "sellers": (
        "seller_id",
        "seller_zip_code_prefix",
        "seller_city",
        "seller_state",
    ),
    "geolocation_lookup": (
        "zip_code_prefix",
        "latitude",
        "longitude",
        "unique_observation_count",
        "city_variant_count",
        "state_variant_count",
        "city",
        "state",
        "source_observation_count",
        "dq_multiple_state_codes",
    ),
    "geolocation_observations": (
        "geolocation_zip_code_prefix",
        "geolocation_lat",
        "geolocation_lng",
        "geolocation_city",
        "geolocation_state",
    ),
    "orders": (
        "order_id",
        "customer_id",
        "order_status",
        "order_purchase_timestamp",
        "order_estimated_delivery_date",
    ),
    "order_items": (
        "order_id",
        "order_item_id",
        "product_id",
        "seller_id",
        "shipping_limit_date",
        "price",
        "freight_value",
    ),
    "order_payments": (
        "order_id",
        "payment_sequential",
        "payment_type",
        "payment_installments",
        "payment_value",
    ),
    "order_reviews": (
        "review_id",
        "order_id",
        "review_score",
        "review_creation_date",
        "review_answer_timestamp",
    ),
}


def split_sql_statements(sql_text: str) -> list[str]:
    """Split the project's simple DDL script into executable statements.

    The schema intentionally contains no procedural blocks or semicolons inside
    string literals, so a semicolon boundary is sufficient and easy to audit.
    """

    if not sql_text.strip():
        raise ValueError("SQL script is empty.")
    return [statement.strip() for statement in sql_text.split(";") if statement.strip()]


def create_database_engine(settings: DatabaseSettings) -> Engine:
    """Create a SQLAlchemy engine without logging credentials."""

    return create_engine(
        settings.sqlalchemy_url,
        pool_pre_ping=True,
        future=True,
    )


def prepare_processed_table(csv_path: Path | str, spec: TableLoadSpec) -> pd.DataFrame:
    """Load one processed CSV and validate its database-facing columns/types."""

    path = Path(csv_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(
            f"Processed file is missing: {path}. Run scripts/run_data_cleaning.py first."
        )
    frame = pd.read_csv(path, low_memory=False)
    missing = sorted(set(spec.required_columns) - set(frame.columns))
    unexpected = sorted(set(frame.columns) - set(spec.required_columns))
    if missing or unexpected:
        details = []
        if missing:
            details.append(f"missing columns: {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected columns: {', '.join(unexpected)}")
        raise ValueError(f"{spec.file_name} does not match its load contract ({'; '.join(details)}).")

    for column in spec.timestamp_columns:
        source_non_null = frame[column].notna()
        parsed = pd.to_datetime(frame[column], errors="coerce")
        invalid_count = int((source_non_null & parsed.isna()).sum())
        if invalid_count:
            raise ValueError(
                f"{spec.file_name}:{column} contains {invalid_count} invalid timestamp value(s)."
            )
        frame[column] = parsed

    for column in spec.integer_columns:
        numeric = pd.to_numeric(frame[column], errors="coerce")
        invalid_count = int((frame[column].notna() & numeric.isna()).sum())
        non_integer_count = int((numeric.dropna() % 1 != 0).sum())
        if invalid_count or non_integer_count:
            raise ValueError(
                f"{spec.file_name}:{column} cannot be safely loaded as an integer "
                f"({invalid_count} invalid, {non_integer_count} non-integral)."
            )
        frame[column] = numeric.astype("Int64")
    return frame.loc[:, list(spec.required_columns)]


def validate_processed_files(processed_data_dir: Path | str) -> pd.DataFrame:
    """Validate every processed file required by the database load contract."""

    directory = Path(processed_data_dir).expanduser().resolve()
    records: list[dict[str, object]] = []
    prepared_tables: dict[str, pd.DataFrame] = {}
    for spec in TABLE_LOAD_SPECS:
        frame = prepare_processed_table(directory / spec.file_name, spec)
        prepared_tables[spec.table_name] = frame
        records.append(
            {
                "file_name": spec.file_name,
                "table_name": f"{DATABASE_SCHEMA}.{spec.table_name}",
                "row_count": int(len(frame)),
                "column_count": int(len(frame.columns)),
                "status": "passed",
            }
        )
    domain_checks = validate_database_domains(prepared_tables)
    failed_checks = domain_checks.loc[domain_checks["status"].eq("failed")]
    if not failed_checks.empty:
        names = ", ".join(failed_checks["check_name"].astype(str))
        raise ValueError(f"Processed data violates database domains: {names}")
    return pd.DataFrame.from_records(records)


def validate_database_domains(
    prepared_tables: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Mirror important PostgreSQL constraints before opening a connection."""

    records: list[dict[str, object]] = []

    def add_check(name: str, table: str, violation_mask: pd.Series) -> None:
        violation_count = int(violation_mask.fillna(False).sum())
        records.append(
            {
                "check_name": name,
                "table_name": f"{DATABASE_SCHEMA}.{table}",
                "violation_count": violation_count,
                "status": "passed" if violation_count == 0 else "failed",
            }
        )

    for table_name, columns in NOT_NULL_COLUMNS.items():
        frame = prepared_tables.get(table_name)
        if frame is None:
            continue
        for column in columns:
            add_check(
                f"{table_name}.{column}.not_null",
                table_name,
                frame[column].isna(),
            )

    for table_name, column in (
        ("customers", "customer_id"),
        ("customers", "customer_unique_id"),
        ("products", "product_id"),
        ("sellers", "seller_id"),
        ("orders", "order_id"),
        ("orders", "customer_id"),
        ("order_items", "order_id"),
        ("order_items", "product_id"),
        ("order_items", "seller_id"),
        ("order_payments", "order_id"),
        ("order_reviews", "review_id"),
        ("order_reviews", "order_id"),
    ):
        frame = prepared_tables.get(table_name)
        if frame is not None:
            add_check(
                f"{table_name}.{column}.max_length_32",
                table_name,
                frame[column].astype("string").str.len().gt(32),
            )

    for table_name, column in (
        ("customers", "customer_state"),
        ("sellers", "seller_state"),
        ("geolocation_lookup", "state"),
        ("geolocation_observations", "geolocation_state"),
    ):
        frame = prepared_tables.get(table_name)
        if frame is not None:
            add_check(
                f"{table_name}.{column}.length_2",
                table_name,
                frame[column].astype("string").str.len().ne(2),
            )

    orders = prepared_tables.get("orders")
    if orders is not None:
        allowed_statuses = {
            "approved", "canceled", "created", "delivered", "invoiced",
            "processing", "shipped", "unavailable",
        }
        add_check(
            "orders.order_status.allowed_values",
            "orders",
            ~orders["order_status"].isin(allowed_statuses),
        )

    items = prepared_tables.get("order_items")
    if items is not None:
        add_check("order_items.price.nonnegative", "order_items", items["price"].lt(0))
        add_check(
            "order_items.freight_value.nonnegative",
            "order_items",
            items["freight_value"].lt(0),
        )

    payments = prepared_tables.get("order_payments")
    if payments is not None:
        add_check(
            "order_payments.payment_value.nonnegative",
            "order_payments",
            payments["payment_value"].lt(0),
        )
        add_check(
            "order_payments.payment_installments.nonnegative",
            "order_payments",
            payments["payment_installments"].lt(0),
        )

    reviews = prepared_tables.get("order_reviews")
    if reviews is not None:
        add_check(
            "order_reviews.review_score.between_1_and_5",
            "order_reviews",
            ~reviews["review_score"].between(1, 5),
        )

    for table_name, latitude_column, longitude_column in (
        ("geolocation_lookup", "latitude", "longitude"),
        ("geolocation_observations", "geolocation_lat", "geolocation_lng"),
    ):
        frame = prepared_tables.get(table_name)
        if frame is not None:
            add_check(
                f"{table_name}.coordinate_bounds",
                table_name,
                ~frame[latitude_column].between(-90, 90)
                | ~frame[longitude_column].between(-180, 180),
            )

    return pd.DataFrame.from_records(
        records,
        columns=["check_name", "table_name", "violation_count", "status"],
    )


def _execute_schema(connection: Connection, schema_sql: str, *, recreate: bool) -> None:
    """Create the database schema inside the active transaction."""

    if recreate:
        connection.exec_driver_sql(f"DROP SCHEMA IF EXISTS {DATABASE_SCHEMA} CASCADE")
    for statement in split_sql_statements(schema_sql):
        connection.exec_driver_sql(statement)


def _truncate_tables(connection: Connection, specs: Iterable[TableLoadSpec]) -> None:
    """Clear managed tables so rerunning the loader is idempotent."""

    qualified_tables = ", ".join(
        f"{DATABASE_SCHEMA}.{spec.table_name}" for spec in reversed(tuple(specs))
    )
    connection.exec_driver_sql(
        f"TRUNCATE TABLE {qualified_tables} RESTART IDENTITY CASCADE"
    )


def load_processed_data(
    engine: Engine,
    processed_data_dir: Path | str,
    schema_sql_path: Path | str,
    quality_sql_path: Path | str,
    *,
    recreate_schema: bool = False,
    chunksize: int = 5_000,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load all processed tables atomically and execute database quality checks.

    Returns:
        A table of loaded row counts and the SQL quality-check result.

    Raises:
        ValueError: If inputs are invalid or a database quality check fails.
    """

    if chunksize < 1:
        raise ValueError("chunksize must be at least 1.")
    directory = Path(processed_data_dir).expanduser().resolve()
    schema_path = Path(schema_sql_path).expanduser().resolve()
    quality_path = Path(quality_sql_path).expanduser().resolve()
    if not schema_path.is_file() or not quality_path.is_file():
        raise FileNotFoundError("Schema SQL or data-quality SQL file is missing.")

    prepared_tables = {
        spec.table_name: prepare_processed_table(directory / spec.file_name, spec)
        for spec in TABLE_LOAD_SPECS
    }
    domain_checks = validate_database_domains(prepared_tables)
    failed_domains = domain_checks.loc[domain_checks["status"].eq("failed")]
    if not failed_domains.empty:
        names = ", ".join(failed_domains["check_name"].astype(str))
        raise ValueError(f"Processed data violates database domains: {names}")
    schema_sql = schema_path.read_text(encoding="utf-8")
    quality_sql = quality_path.read_text(encoding="utf-8")
    load_records: list[dict[str, object]] = []

    with engine.begin() as connection:
        _execute_schema(connection, schema_sql, recreate=recreate_schema)
        _truncate_tables(connection, TABLE_LOAD_SPECS)
        for spec in TABLE_LOAD_SPECS:
            frame = prepared_tables[spec.table_name]
            frame.to_sql(
                spec.table_name,
                connection,
                schema=DATABASE_SCHEMA,
                if_exists="append",
                index=False,
                chunksize=chunksize,
                method=None,
            )
            database_count = int(
                connection.execute(
                    text(f"SELECT COUNT(*) FROM {DATABASE_SCHEMA}.{spec.table_name}")
                ).scalar_one()
            )
            if database_count != len(frame):
                raise ValueError(
                    f"Row-count verification failed for {spec.table_name}: "
                    f"expected {len(frame)}, found {database_count}."
                )
            load_records.append(
                {
                    "table_name": f"{DATABASE_SCHEMA}.{spec.table_name}",
                    "loaded_rows": database_count,
                    "status": "passed",
                }
            )

        quality_checks = pd.read_sql_query(text(quality_sql), connection)
        failed_checks = quality_checks.loc[quality_checks["status"].eq("failed")]
        if not failed_checks.empty:
            names = ", ".join(failed_checks["check_name"].astype(str))
            raise ValueError(f"Database quality checks failed: {names}")

    return pd.DataFrame.from_records(load_records), quality_checks

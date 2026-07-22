"""Tests for declared Olist relational contracts."""

import pandas as pd

from src.relational_quality import (
    build_business_rule_check_table,
    build_key_check_table,
    build_relationship_check_table,
)


def test_composite_key_check_detects_duplicate_order_items() -> None:
    """Composite keys must be evaluated as a unit rather than column by column."""

    tables = {
        "olist_order_items_dataset.csv": pd.DataFrame(
            {
                "order_id": ["one", "one"],
                "order_item_id": [1, 1],
            }
        )
    }

    result = build_key_check_table(tables)
    item_check = result.loc[
        result["file_name"].eq("olist_order_items_dataset.csv")
    ].iloc[0]

    assert item_check["primary_key"] == "order_id + order_item_id"
    assert item_check["duplicate_key_rows"] == 2
    assert item_check["status"] == "failed"


def test_relationship_check_counts_orphan_child_keys() -> None:
    """Foreign-key checks should report unmatched non-null child values."""

    tables = {
        "olist_orders_dataset.csv": pd.DataFrame(
            {"order_id": ["order-1"], "customer_id": ["missing-customer"]}
        ),
        "olist_customers_dataset.csv": pd.DataFrame(
            {"customer_id": ["customer-1"]}
        ),
    }

    result = build_relationship_check_table(tables)
    check = result.loc[result["relationship"].eq("orders_to_customers")].iloc[0]

    assert check["orphan_rows"] == 1
    assert check["distinct_orphan_keys"] == 1
    assert check["status"] == "failed"


def test_timestamp_rule_marks_reversed_sequence_for_review() -> None:
    """Chronological exceptions should be surfaced without changing values."""

    tables = {
        "olist_orders_dataset.csv": pd.DataFrame(
            {
                "order_status": ["delivered"],
                "order_purchase_timestamp": ["2024-01-02"],
                "order_approved_at": ["2024-01-01"],
            }
        )
    }

    result = build_business_rule_check_table(tables)
    check = result.loc[result["rule_name"].eq("purchase_before_approval")].iloc[0]

    assert check["comparable_rows"] == 1
    assert check["violation_rows"] == 1
    assert check["status"] == "review"


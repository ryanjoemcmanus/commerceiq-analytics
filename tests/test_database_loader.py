"""Tests for PostgreSQL load contracts and SQL preparation."""

from pathlib import Path

import pandas as pd
import pytest

from src.database_loader import (
    TableLoadSpec,
    prepare_processed_table,
    split_sql_statements,
    validate_database_domains,
)


def test_split_sql_statements_rejects_empty_script() -> None:
    """An empty schema must fail before any database connection is attempted."""

    with pytest.raises(ValueError, match="empty"):
        split_sql_statements("  \n")


def test_split_sql_statements_returns_executable_units() -> None:
    """The project DDL style should split at explicit statement boundaries."""

    statements = split_sql_statements(
        "CREATE SCHEMA demo; CREATE TABLE demo.example (id INTEGER);"
    )

    assert statements == [
        "CREATE SCHEMA demo",
        "CREATE TABLE demo.example (id INTEGER)",
    ]


def test_prepare_processed_table_validates_and_converts_types(tmp_path: Path) -> None:
    """Database-facing timestamps and integers should be explicit before loading."""

    csv_path = tmp_path / "example.csv"
    pd.DataFrame(
        {"id": [1, 2], "event_at": ["2024-01-01", "2024-01-02"]}
    ).to_csv(csv_path, index=False)
    spec = TableLoadSpec(
        file_name="example.csv",
        table_name="example",
        required_columns=("id", "event_at"),
        timestamp_columns=("event_at",),
        integer_columns=("id",),
    )

    result = prepare_processed_table(csv_path, spec)

    assert str(result["id"].dtype) == "Int64"
    assert pd.api.types.is_datetime64_any_dtype(result["event_at"])


def test_prepare_processed_table_rejects_contract_drift(tmp_path: Path) -> None:
    """Missing or unexpected columns should stop a database load."""

    csv_path = tmp_path / "example.csv"
    pd.DataFrame({"id": [1], "unexpected": [2]}).to_csv(csv_path, index=False)
    spec = TableLoadSpec(
        file_name="example.csv",
        table_name="example",
        required_columns=("id", "required_value"),
    )

    with pytest.raises(ValueError, match="missing columns.*unexpected columns"):
        prepare_processed_table(csv_path, spec)


def test_schema_contains_core_relational_constraints() -> None:
    """The checked-in DDL should expose the intended portfolio data model."""

    schema_path = Path(__file__).resolve().parents[1] / "sql" / "schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8").lower()

    assert "create schema if not exists commerceiq" in schema_sql
    assert "primary key (order_id, order_item_id)" in schema_sql
    assert "primary key (review_id, order_id)" in schema_sql
    assert "foreign key (customer_id)" in schema_sql
    assert "check (review_score between 1 and 5)" in schema_sql


def test_database_domain_validation_detects_invalid_review_score() -> None:
    """Offline checks should mirror database domains before a connection."""

    reports = validate_database_domains(
        {
            "order_reviews": pd.DataFrame(
                {
                    "review_id": ["review-1"],
                    "order_id": ["order-1"],
                    "review_score": [6],
                    "review_creation_date": [pd.Timestamp("2024-01-01")],
                    "review_answer_timestamp": [pd.Timestamp("2024-01-02")],
                }
            )
        }
    )
    score_check = reports.loc[
        reports["check_name"].eq("order_reviews.review_score.between_1_and_5")
    ].iloc[0]

    assert score_check["violation_count"] == 1
    assert score_check["status"] == "failed"

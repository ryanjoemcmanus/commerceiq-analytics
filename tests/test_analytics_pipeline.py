"""Tests for named SQL parsing and analytical result contracts."""

import pandas as pd
import pytest

from src.analytics_pipeline import parse_named_queries, validate_analytics_result


def test_parse_named_queries_preserves_query_order() -> None:
    """Named sections should be parsed without relying on semicolon splitting."""

    queries = parse_named_queries(
        """-- heading
-- name: first_query
SELECT 1 AS value;
-- name: second_query
SELECT 2 AS value;
"""
    )

    assert list(queries) == ["first_query", "second_query"]
    assert queries["first_query"] == "SELECT 1 AS value"


def test_parse_named_queries_rejects_duplicate_names() -> None:
    """Duplicate output names would overwrite extracts and must be rejected."""

    with pytest.raises(ValueError, match="Duplicate"):
        parse_named_queries(
            "-- name: duplicate\nSELECT 1;\n-- name: duplicate\nSELECT 2;"
        )


def test_validate_analytics_result_rejects_column_drift() -> None:
    """A changed SQL output must not silently break the presentation layer."""

    with pytest.raises(ValueError, match="contract mismatch"):
        validate_analytics_result(
            "order_status_distribution",
            pd.DataFrame({"wrong_column": [1]}),
        )


def test_validate_analytics_result_accepts_documented_contract() -> None:
    """A populated result with exact documented columns should pass."""

    frame = pd.DataFrame(
        {
            "order_status": ["delivered"],
            "order_count": [1],
            "order_share_pct": [100.0],
        }
    )

    validate_analytics_result("order_status_distribution", frame)


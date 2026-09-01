"""Execute named PostgreSQL analytics queries and export reproducible results."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import Engine, text

QUERY_NAME_PATTERN = re.compile(r"^--\s*name:\s*([a-z][a-z0-9_]*)\s*$", re.MULTILINE)

ANALYTICS_RESULT_CONTRACTS = {
    "executive_summary": (
        "first_order_date",
        "last_order_date",
        "total_orders",
        "delivered_orders",
        "unique_customers",
        "active_sellers",
        "delivered_gmv",
        "delivered_average_order_value",
        "cancellation_rate_pct",
        "on_time_delivery_rate_pct",
        "average_delivery_days",
        "average_review_score",
        "low_review_rate_pct",
        "repeat_customer_rate_pct",
    ),
    "monthly_performance": (
        "order_month",
        "total_orders",
        "delivered_orders",
        "canceled_orders",
        "delivered_gmv",
        "delivered_average_order_value",
        "cancellation_rate_pct",
        "on_time_delivery_rate_pct",
        "average_delivery_days",
        "average_review_score",
    ),
    "category_performance": (
        "category_name",
        "delivered_orders",
        "items_sold",
        "delivered_gmv",
        "freight_revenue",
        "average_item_price",
        "average_review_score",
    ),
    "state_performance": (
        "customer_state",
        "total_orders",
        "delivered_orders",
        "delivered_gmv",
        "cancellation_rate_pct",
        "on_time_delivery_rate_pct",
        "average_review_score",
    ),
    "payment_method_performance": (
        "payment_type",
        "payment_records",
        "orders_using_method",
        "payment_value",
        "average_payment_record_value",
        "average_installments",
        "payment_value_share_pct",
    ),
    "order_status_distribution": (
        "order_status",
        "order_count",
        "order_share_pct",
    ),
    "delivery_review_relationship": (
        "delivery_timing_band",
        "band_order",
        "delivered_orders",
        "average_delay_days",
        "average_review_score",
        "low_review_rate_pct",
    ),
    "customer_purchase_frequency": (
        "frequency_band",
        "band_order",
        "customers",
        "customer_share_pct",
        "average_delivered_orders",
    ),
    "monthly_customer_cohorts": (
        "cohort_month",
        "month_number",
        "cohort_size",
        "active_customers",
        "retention_rate_pct",
    ),
    "seller_scorecard": (
        "seller_id",
        "seller_state",
        "delivered_orders",
        "delivered_gmv",
        "average_order_revenue",
        "on_time_delivery_rate_pct",
        "average_review_score",
        "low_review_rate_pct",
    ),
}


def _sha256(path: Path) -> str:
    """Return a streaming SHA-256 digest for a file."""

    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_named_queries(sql_text: str) -> dict[str, str]:
    """Parse ``-- name: query_name`` sections from a SQL file."""

    matches = list(QUERY_NAME_PATTERN.finditer(sql_text))
    if not matches:
        raise ValueError("SQL text contains no '-- name:' query markers.")

    queries: dict[str, str] = {}
    for index, match in enumerate(matches):
        name = match.group(1)
        if name in queries:
            raise ValueError(f"Duplicate named SQL query: {name}")
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(sql_text)
        query = sql_text[start:end].strip().removesuffix(";").strip()
        if not query:
            raise ValueError(f"Named SQL query {name!r} is empty.")
        queries[name] = query
    return queries


def load_named_query_files(sql_paths: Iterable[Path | str]) -> dict[str, str]:
    """Load named queries from one or more SQL files and enforce uniqueness."""

    combined: dict[str, str] = {}
    for sql_path in sql_paths:
        path = Path(sql_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Analytics SQL file was not found: {path}")
        for name, query in parse_named_queries(path.read_text(encoding="utf-8")).items():
            if name in combined:
                raise ValueError(f"Duplicate query name across SQL files: {name}")
            combined[name] = query
    return combined


def validate_analytics_result(query_name: str, frame: pd.DataFrame) -> None:
    """Validate an analytical extract against its documented output columns."""

    expected = ANALYTICS_RESULT_CONTRACTS.get(query_name)
    if expected is None:
        raise ValueError(f"No result contract is defined for query: {query_name}")
    actual = tuple(str(column) for column in frame.columns)
    if actual != expected:
        raise ValueError(
            f"Result contract mismatch for {query_name}: expected {expected}, found {actual}."
        )
    if frame.empty:
        raise ValueError(f"Analytics query returned no rows: {query_name}")


def _write_csv(frame: pd.DataFrame, destination: Path) -> None:
    """Write an analytical CSV atomically."""

    temporary = destination.with_suffix(destination.suffix + ".tmp")
    frame.to_csv(temporary, index=False, encoding="utf-8", date_format="%Y-%m-%d")
    temporary.replace(destination)


def run_analytics_pipeline(
    engine: Engine,
    sql_paths: Iterable[Path | str],
    output_dir: Path | str,
) -> dict[str, object]:
    """Execute all named queries and export validated analytical extracts."""

    resolved_paths = [Path(path).expanduser().resolve() for path in sql_paths]
    queries = load_named_query_files(resolved_paths)
    output_directory = Path(output_dir).expanduser().resolve()
    output_directory.mkdir(parents=True, exist_ok=True)

    result_records: list[dict[str, object]] = []
    with engine.connect() as connection:
        for query_name, query in queries.items():
            frame = pd.read_sql_query(text(query), connection)
            validate_analytics_result(query_name, frame)
            output_path = output_directory / f"{query_name}.csv"
            _write_csv(frame, output_path)
            result_records.append(
                {
                    "query_name": query_name,
                    "output_file": str(output_path),
                    "row_count": int(len(frame)),
                    "columns": [str(column) for column in frame.columns],
                    "query_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
                    "output_sha256": _sha256(output_path),
                }
            )

    manifest: dict[str, object] = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "query_count": len(queries),
        "sql_files": [
            {"path": str(path), "sha256": _sha256(path)} for path in resolved_paths
        ],
        "results": result_records,
    }
    manifest_path = output_directory / "analytics_manifest.json"
    temporary_manifest = manifest_path.with_suffix(".json.tmp")
    temporary_manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary_manifest.replace(manifest_path)
    return manifest


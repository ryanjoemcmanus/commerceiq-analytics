"""Schema, key, relationship, and business-rule checks for Olist source data."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pandas as pd

from src.data_cleaning import discover_csv_files, load_csv_safely
from src.data_contracts import (
    ALLOWED_ORDER_STATUSES,
    FOREIGN_KEY_CONTRACTS,
    TABLE_CONTRACTS,
    TIMESTAMP_ORDER_CONTRACTS,
)


def load_source_tables(raw_data_dir: Path | str) -> dict[str, pd.DataFrame]:
    """Load discovered CSVs into a file-name keyed mapping.

    Raises:
        ValueError: If recursive discovery finds duplicate CSV file names.
    """

    tables: dict[str, pd.DataFrame] = {}
    for path in discover_csv_files(raw_data_dir):
        if path.name in tables:
            raise ValueError(
                f"Duplicate CSV file name found below raw data: {path.name}. "
                "Remove duplicate extracted copies before running relational checks."
            )
        tables[path.name] = load_csv_safely(path)
    return tables


def build_schema_check_table(tables: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    """Compare actual source columns with the declared table contracts."""

    records: list[dict[str, object]] = []
    for file_name, contract in TABLE_CONTRACTS.items():
        frame = tables.get(file_name)
        if frame is None:
            records.append(
                {
                    "file_name": file_name,
                    "status": "failed",
                    "missing_columns": "ALL — source file missing",
                    "unexpected_columns": "",
                    "expected_column_count": len(contract.required_columns),
                    "actual_column_count": 0,
                }
            )
            continue

        actual_columns = set(str(column) for column in frame.columns)
        required_columns = set(contract.required_columns)
        missing = sorted(required_columns - actual_columns)
        unexpected = sorted(actual_columns - required_columns)
        status = "failed" if missing else "review" if unexpected else "passed"
        records.append(
            {
                "file_name": file_name,
                "status": status,
                "missing_columns": " | ".join(missing),
                "unexpected_columns": " | ".join(unexpected),
                "expected_column_count": len(required_columns),
                "actual_column_count": len(actual_columns),
            }
        )
    return pd.DataFrame.from_records(
        records,
        columns=[
            "file_name",
            "status",
            "missing_columns",
            "unexpected_columns",
            "expected_column_count",
            "actual_column_count",
        ],
    )


def build_key_check_table(tables: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    """Check declared single-column and composite primary keys."""

    records: list[dict[str, object]] = []
    for file_name, contract in TABLE_CONTRACTS.items():
        if not contract.primary_key or file_name not in tables:
            continue
        frame = tables[file_name]
        key_columns = list(contract.primary_key)
        if any(column not in frame.columns for column in key_columns):
            continue

        null_key_rows = int(frame[key_columns].isna().any(axis=1).sum())
        duplicate_key_rows = int(frame.duplicated(key_columns, keep=False).sum())
        duplicate_key_occurrences = int(frame.duplicated(key_columns).sum())
        records.append(
            {
                "file_name": file_name,
                "grain": contract.grain,
                "primary_key": " + ".join(key_columns),
                "row_count": int(frame.shape[0]),
                "null_key_rows": null_key_rows,
                "duplicate_key_rows": duplicate_key_rows,
                "duplicate_key_occurrences": duplicate_key_occurrences,
                "status": (
                    "passed"
                    if null_key_rows == 0 and duplicate_key_rows == 0
                    else "failed"
                ),
            }
        )
    return pd.DataFrame.from_records(
        records,
        columns=[
            "file_name",
            "grain",
            "primary_key",
            "row_count",
            "null_key_rows",
            "duplicate_key_rows",
            "duplicate_key_occurrences",
            "status",
        ],
    )


def build_relationship_check_table(tables: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    """Measure foreign-key coverage for each declared relationship."""

    records: list[dict[str, object]] = []
    for contract in FOREIGN_KEY_CONTRACTS:
        child = tables.get(contract.child_file)
        parent = tables.get(contract.parent_file)
        required_columns_available = (
            child is not None
            and parent is not None
            and contract.child_column in child.columns
            and contract.parent_column in parent.columns
        )
        if not required_columns_available:
            records.append(
                {
                    "relationship": contract.name,
                    "child_reference": f"{contract.child_file}:{contract.child_column}",
                    "parent_reference": f"{contract.parent_file}:{contract.parent_column}",
                    "child_rows": 0,
                    "null_child_keys": 0,
                    "orphan_rows": 0,
                    "distinct_orphan_keys": 0,
                    "matched_non_null_percent": 0.0,
                    "status": "failed",
                }
            )
            continue

        assert child is not None and parent is not None
        child_keys = child[contract.child_column]
        parent_keys = set(parent[contract.parent_column].dropna())
        non_null_mask = child_keys.notna()
        orphan_mask = non_null_mask & ~child_keys.isin(parent_keys)
        non_null_count = int(non_null_mask.sum())
        orphan_rows = int(orphan_mask.sum())
        matched_percent = (
            round(((non_null_count - orphan_rows) / non_null_count) * 100, 4)
            if non_null_count
            else 100.0
        )
        null_rows = int((~non_null_mask).sum())
        has_violation = orphan_rows > 0 or (null_rows > 0 and not contract.nullable)
        status = (
            "failed"
            if has_violation and contract.strict
            else "review"
            if has_violation
            else "passed"
        )
        records.append(
            {
                "relationship": contract.name,
                "child_reference": f"{contract.child_file}:{contract.child_column}",
                "parent_reference": f"{contract.parent_file}:{contract.parent_column}",
                "child_rows": int(child.shape[0]),
                "null_child_keys": null_rows,
                "orphan_rows": orphan_rows,
                "distinct_orphan_keys": int(child_keys[orphan_mask].nunique()),
                "matched_non_null_percent": matched_percent,
                "status": status,
            }
        )
    return pd.DataFrame.from_records(
        records,
        columns=[
            "relationship",
            "child_reference",
            "parent_reference",
            "child_rows",
            "null_child_keys",
            "orphan_rows",
            "distinct_orphan_keys",
            "matched_non_null_percent",
            "status",
        ],
    )


def build_business_rule_check_table(tables: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    """Check controlled values and chronological business rules."""

    records: list[dict[str, object]] = []
    orders = tables.get("olist_orders_dataset.csv")
    if orders is not None and "order_status" in orders.columns:
        statuses = orders["order_status"]
        unexpected_mask = statuses.notna() & ~statuses.isin(ALLOWED_ORDER_STATUSES)
        records.append(
            {
                "rule_name": "allowed_order_status",
                "file_name": "olist_orders_dataset.csv",
                "rule_type": "allowed_values",
                "comparable_rows": int(statuses.notna().sum()),
                "violation_rows": int(unexpected_mask.sum()),
                "violation_percent": round(float(unexpected_mask.mean() * 100), 4),
                "details": " | ".join(sorted(statuses[unexpected_mask].astype(str).unique())),
                "status": "passed" if not unexpected_mask.any() else "failed",
            }
        )

    for contract in TIMESTAMP_ORDER_CONTRACTS:
        frame = tables.get(contract.file_name)
        if (
            frame is None
            or contract.earlier_column not in frame.columns
            or contract.later_column not in frame.columns
        ):
            continue
        earlier = pd.to_datetime(frame[contract.earlier_column], errors="coerce")
        later = pd.to_datetime(frame[contract.later_column], errors="coerce")
        comparable_mask = earlier.notna() & later.notna()
        violation_mask = comparable_mask & (earlier > later)
        comparable_rows = int(comparable_mask.sum())
        violation_rows = int(violation_mask.sum())
        records.append(
            {
                "rule_name": contract.name,
                "file_name": contract.file_name,
                "rule_type": "timestamp_order",
                "comparable_rows": comparable_rows,
                "violation_rows": violation_rows,
                "violation_percent": (
                    round((violation_rows / comparable_rows) * 100, 4)
                    if comparable_rows
                    else 0.0
                ),
                "details": f"{contract.earlier_column} <= {contract.later_column}",
                "status": "passed" if violation_rows == 0 else "review",
            }
        )
    return pd.DataFrame.from_records(
        records,
        columns=[
            "rule_name",
            "file_name",
            "rule_type",
            "comparable_rows",
            "violation_rows",
            "violation_percent",
            "details",
            "status",
        ],
    )


def build_relational_quality_reports(
    raw_data_dir: Path | str,
) -> dict[str, pd.DataFrame]:
    """Load source data once and calculate all relational-quality reports."""

    tables = load_source_tables(raw_data_dir)
    return {
        "schema_checks": build_schema_check_table(tables),
        "key_checks": build_key_check_table(tables),
        "relationship_checks": build_relationship_check_table(tables),
        "business_rule_checks": build_business_rule_check_table(tables),
    }

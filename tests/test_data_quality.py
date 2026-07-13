"""Tests for structured data-quality report generation."""

import json
from pathlib import Path

import pandas as pd

from src.data_cleaning import audit_dataframe
from src.data_quality import (
    REPORT_FILE_NAMES,
    build_column_quality_table,
    run_data_quality_audit,
)


def test_build_column_quality_table_calculates_missing_percent() -> None:
    """Column-level output should expose calculated missingness."""

    audit = audit_dataframe(
        pd.DataFrame({"order_id": ["a", "b"], "value": [1.0, None]}),
        file_name="orders.csv",
    )

    result = build_column_quality_table([audit]).set_index("column_name")

    assert result.loc["value", "missing_values"] == 1
    assert result.loc["value", "missing_percent"] == 50.0
    assert bool(result.loc["order_id", "likely_primary_key"])


def test_run_data_quality_audit_exports_all_reports(tmp_path: Path) -> None:
    """The pipeline should write every documented report from real CSV input."""

    raw_directory = tmp_path / "raw"
    report_directory = tmp_path / "reports"
    raw_directory.mkdir()
    pd.DataFrame(
        {
            "order_id": ["one", "two"],
            "created_at": ["2024-01-01", "invalid"],
        }
    ).to_csv(raw_directory / "orders.csv", index=False)

    summary = run_data_quality_audit(raw_directory, report_directory)

    assert summary["audited_file_count"] == 1
    assert summary["load_error_count"] == 0
    assert {path.name for path in report_directory.iterdir()} == set(
        REPORT_FILE_NAMES.values()
    )

    saved_summary = json.loads(
        (report_directory / REPORT_FILE_NAMES["audit_summary"]).read_text(encoding="utf-8")
    )
    assert saved_summary["tables"][0]["file_name"] == "orders.csv"


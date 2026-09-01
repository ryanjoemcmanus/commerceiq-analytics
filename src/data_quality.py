"""Reporting pipeline for the CommerceIQ source-data quality audit."""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.data_cleaning import (
    TableAudit,
    audit_csv_directory,
    build_overview_table,
    discover_csv_files,
)
from src.relational_quality import build_relational_quality_reports

REPORT_FILE_NAMES = {
    "table_overview": "table_overview.csv",
    "column_quality": "column_quality.csv",
    "timestamp_issues": "timestamp_issues.csv",
    "issue_register": "issue_register.csv",
    "schema_checks": "schema_checks.csv",
    "key_checks": "key_checks.csv",
    "relationship_checks": "relationship_checks.csv",
    "business_rule_checks": "business_rule_checks.csv",
    "audit_summary": "audit_summary.json",
}


def build_column_quality_table(audits: Iterable[TableAudit]) -> pd.DataFrame:
    """Build one record per source column with type and missingness metrics."""

    records: list[dict[str, Any]] = []
    for audit in audits:
        for column in audit.column_names:
            missing_count = audit.missing_values[column]
            missing_percent = (
                round((missing_count / audit.row_count) * 100, 4)
                if audit.row_count
                else 0.0
            )
            records.append(
                {
                    "file_name": audit.file_name,
                    "column_name": column,
                    "inferred_dtype": audit.inferred_dtypes[column],
                    "missing_values": missing_count,
                    "missing_percent": missing_percent,
                    "likely_primary_key": column in audit.likely_primary_keys,
                }
            )
    return pd.DataFrame.from_records(
        records,
        columns=[
            "file_name",
            "column_name",
            "inferred_dtype",
            "missing_values",
            "missing_percent",
            "likely_primary_key",
        ],
    )


def build_timestamp_issue_table(audits: Iterable[TableAudit]) -> pd.DataFrame:
    """Build one record per timestamp-like column checked by the audit."""

    records = [
        {
            "file_name": audit.file_name,
            "column_name": issue.column,
            "non_null_values": issue.non_null_values,
            "invalid_values": issue.invalid_values,
            "invalid_percent": (
                round((issue.invalid_values / issue.non_null_values) * 100, 4)
                if issue.non_null_values
                else 0.0
            ),
            "invalid_examples": " | ".join(issue.invalid_examples),
        }
        for audit in audits
        for issue in audit.timestamp_issues
    ]
    return pd.DataFrame.from_records(
        records,
        columns=[
            "file_name",
            "column_name",
            "non_null_values",
            "invalid_values",
            "invalid_percent",
            "invalid_examples",
        ],
    )


def build_issue_register(
    audits: Iterable[TableAudit],
    load_errors: dict[str, str],
) -> pd.DataFrame:
    """Build a consolidated register of calculated warnings and load failures."""

    records = [
        {
            "file_name": audit.file_name,
            "issue_type": "quality_warning",
            "message": warning,
        }
        for audit in audits
        for warning in audit.warnings
    ]
    records.extend(
        {
            "file_name": file_name,
            "issue_type": "load_error",
            "message": message,
        }
        for file_name, message in sorted(load_errors.items())
    )
    return pd.DataFrame.from_records(
        records,
        columns=["file_name", "issue_type", "message"],
    )


def _write_json(payload: dict[str, Any], destination: Path) -> None:
    """Write human-readable UTF-8 JSON to a validated destination."""

    with destination.open("w", encoding="utf-8") as output_file:
        json.dump(payload, output_file, indent=2, ensure_ascii=False)
        output_file.write("\n")


def _build_relational_issue_register(
    relational_reports: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Convert non-passing relational checks into investigation prompts."""

    records: list[dict[str, str]] = []
    for report_name, report in relational_reports.items():
        if report.empty or "status" not in report.columns:
            continue
        for record in report.loc[report["status"].ne("passed")].to_dict("records"):
            file_name = str(record.get("file_name") or record.get("child_reference", "")).split(":")[0]
            identifier = str(
                record.get("rule_name")
                or record.get("relationship")
                or record.get("primary_key")
                or file_name
            )
            records.append(
                {
                    "file_name": file_name,
                    "issue_type": report_name.removesuffix("_checks"),
                    "message": f"{identifier} returned status '{record['status']}'.",
                }
            )
    return pd.DataFrame.from_records(
        records,
        columns=["file_name", "issue_type", "message"],
    )


def run_data_quality_audit(
    raw_data_dir: Path | str,
    report_dir: Path | str,
) -> dict[str, Any]:
    """Audit all source CSVs and export reproducible CSV and JSON reports.

    The function never writes to ``raw_data_dir``. Existing report files with
    the standard names are replaced so each run represents current source data.

    Raises:
        FileNotFoundError: If no CSV files are available below the raw directory.
        NotADirectoryError: If the raw-data path does not exist.
    """

    raw_directory = Path(raw_data_dir).expanduser().resolve()
    output_directory = Path(report_dir).expanduser().resolve()
    source_files = discover_csv_files(raw_directory)
    if not source_files:
        raise FileNotFoundError(
            f"No CSV files were found below {raw_directory}. Add the Olist source files first."
        )

    audits, load_errors = audit_csv_directory(raw_directory)
    output_directory.mkdir(parents=True, exist_ok=True)

    relational_reports = build_relational_quality_reports(raw_directory)
    issue_register = build_issue_register(audits, load_errors)
    relational_issues = _build_relational_issue_register(relational_reports)
    if not relational_issues.empty:
        issue_register = pd.concat([issue_register, relational_issues], ignore_index=True)

    report_tables = {
        "table_overview": build_overview_table(audits),
        "column_quality": build_column_quality_table(audits),
        "timestamp_issues": build_timestamp_issue_table(audits),
        "issue_register": issue_register,
        **relational_reports,
    }
    for report_name, table in report_tables.items():
        table.to_csv(output_directory / REPORT_FILE_NAMES[report_name], index=False)

    summary: dict[str, Any] = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source_directory": str(raw_directory),
        "report_directory": str(output_directory),
        "discovered_file_count": len(source_files),
        "audited_file_count": len(audits),
        "load_error_count": len(load_errors),
        "total_rows_across_source_tables": sum(audit.row_count for audit in audits),
        "report_files": REPORT_FILE_NAMES,
        "load_errors": load_errors,
        "relational_status_counts": {
            report_name: {
                str(status): int(count)
                for status, count in report["status"].value_counts().items()
            }
            for report_name, report in relational_reports.items()
            if "status" in report.columns
        },
        "tables": [audit.to_dict() for audit in audits],
    }
    _write_json(summary, output_directory / REPORT_FILE_NAMES["audit_summary"])
    return summary

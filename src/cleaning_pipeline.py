"""Orchestration for reproducible CommerceIQ processed-data generation."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.data_cleaning import (
    CleaningResult,
    build_geolocation_lookup,
    clean_source_table,
    discover_csv_files,
)
from src.data_contracts import TABLE_CONTRACTS
from src.relational_quality import (
    build_business_rule_check_table,
    build_key_check_table,
    build_relationship_check_table,
    build_schema_check_table,
    load_source_tables,
)

MANIFEST_FILE_NAME = "cleaning_manifest.json"
VALIDATION_REPORT_FILES = {
    "key_checks": "post_cleaning_key_checks.csv",
    "relationship_checks": "post_cleaning_relationship_checks.csv",
    "business_rule_checks": "post_cleaning_business_rule_checks.csv",
}


def _sha256(path: Path) -> str:
    """Return a streaming SHA-256 digest for a file."""

    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_csv(frame: pd.DataFrame, destination: Path) -> None:
    """Write a CSV atomically so interrupted runs do not leave partial files."""

    temporary = destination.with_suffix(destination.suffix + ".tmp")
    frame.to_csv(
        temporary,
        index=False,
        encoding="utf-8",
        date_format="%Y-%m-%d %H:%M:%S",
    )
    temporary.replace(destination)


def _write_json(payload: dict[str, Any], destination: Path) -> None:
    """Write UTF-8 JSON atomically."""

    temporary = destination.with_suffix(destination.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as output_file:
        json.dump(payload, output_file, indent=2, ensure_ascii=False)
        output_file.write("\n")
    temporary.replace(destination)


def _quality_flag_counts(frame: pd.DataFrame) -> dict[str, int]:
    """Count true values in generated data-quality flag columns."""

    return {
        column: int(frame[column].fillna(False).astype(bool).sum())
        for column in frame.columns
        if str(column).startswith("dq_")
    }


def clean_all_source_tables(
    source_tables: dict[str, pd.DataFrame],
) -> dict[str, CleaningResult]:
    """Clean every contracted Olist source table in dependency-safe order."""

    schema_checks = build_schema_check_table(source_tables)
    failed_schemas = schema_checks.loc[schema_checks["status"].eq("failed")]
    if not failed_schemas.empty:
        failed_names = ", ".join(failed_schemas["file_name"].tolist())
        raise ValueError(f"Cleaning stopped because source schema checks failed: {failed_names}")

    source_key_checks = build_key_check_table(source_tables)
    source_relationship_checks = build_relationship_check_table(source_tables)
    if source_key_checks["status"].eq("failed").any():
        raise ValueError("Cleaning stopped because a declared source key check failed.")
    if source_relationship_checks["status"].eq("failed").any():
        raise ValueError("Cleaning stopped because a strict source relationship check failed.")

    translation_name = "product_category_name_translation.csv"
    translation = source_tables[translation_name]
    results: dict[str, CleaningResult] = {}
    for file_name in TABLE_CONTRACTS:
        results[file_name] = clean_source_table(
            source_tables[file_name],
            file_name=file_name,
            category_translation=translation if file_name == "olist_products_dataset.csv" else None,
        )

    products = results["olist_products_dataset.csv"].frame
    translation_result = results[translation_name]
    cleaned_translation = translation_result.frame.copy()
    cleaned_translation["dq_translation_missing"] = False
    untranslated_categories = sorted(
        set(products["product_category_name"].dropna())
        - set(cleaned_translation["product_category_name"].dropna())
    )
    if untranslated_categories:
        fallback_rows = pd.DataFrame(
            {
                "product_category_name": untranslated_categories,
                "product_category_name_english": untranslated_categories,
                "dq_translation_missing": True,
            }
        )
        cleaned_translation = pd.concat(
            [cleaned_translation, fallback_rows],
            ignore_index=True,
        )
    cleaned_translation = cleaned_translation.sort_values(
        "product_category_name",
        na_position="last",
    ).reset_index(drop=True)
    results[translation_name] = CleaningResult(
        frame=cleaned_translation,
        applied_rules=translation_result.applied_rules
        + (
            "added untranslated source categories with transparent fallback labels",
            "added missing-translation quality flag",
        ),
    )

    geolocation_name = "olist_geolocation_dataset.csv"
    results["geolocation_lookup.csv"] = build_geolocation_lookup(
        results[geolocation_name].frame,
        source_geolocation=source_tables[geolocation_name],
    )
    return results


def run_cleaning_pipeline(
    raw_data_dir: Path | str,
    processed_data_dir: Path | str,
    report_dir: Path | str,
) -> dict[str, Any]:
    """Clean source tables, validate outputs, and write a detailed manifest."""

    raw_directory = Path(raw_data_dir).expanduser().resolve()
    processed_directory = Path(processed_data_dir).expanduser().resolve()
    report_directory = Path(report_dir).expanduser().resolve()

    source_paths = {path.name: path for path in discover_csv_files(raw_directory)}
    source_tables = load_source_tables(raw_directory)
    cleaned_results = clean_all_source_tables(source_tables)
    cleaned_tables = {
        name: result.frame
        for name, result in cleaned_results.items()
        if name in TABLE_CONTRACTS
    }

    validation_reports = {
        "key_checks": build_key_check_table(cleaned_tables),
        "relationship_checks": build_relationship_check_table(cleaned_tables),
        "business_rule_checks": build_business_rule_check_table(cleaned_tables),
    }
    failed_keys = validation_reports["key_checks"]["status"].eq("failed").any()
    failed_relationships = validation_reports["relationship_checks"]["status"].eq("failed").any()
    if failed_keys or failed_relationships:
        raise ValueError(
            "Cleaning stopped because processed data failed a declared key or strict relationship check."
        )

    processed_directory.mkdir(parents=True, exist_ok=True)
    report_directory.mkdir(parents=True, exist_ok=True)
    for file_name, result in cleaned_results.items():
        _write_csv(result.frame, processed_directory / file_name)
    for report_name, report in validation_reports.items():
        _write_csv(report, report_directory / VALIDATION_REPORT_FILES[report_name])

    table_records: list[dict[str, Any]] = []
    for file_name, result in cleaned_results.items():
        output_path = processed_directory / file_name
        source_path = source_paths.get(file_name)
        source_frame = source_tables.get(file_name)
        input_rows = int(len(source_frame)) if source_frame is not None else None
        table_records.append(
            {
                "source_file": str(source_path) if source_path else None,
                "output_file": str(output_path),
                "input_rows": input_rows,
                "output_rows": int(len(result.frame)),
                "rows_removed": (
                    max(input_rows - len(result.frame), 0) if input_rows is not None else None
                ),
                "rows_added": (
                    max(len(result.frame) - input_rows, 0) if input_rows is not None else None
                ),
                "input_columns": (
                    [str(column) for column in source_frame.columns]
                    if source_frame is not None
                    else None
                ),
                "output_columns": [str(column) for column in result.frame.columns],
                "quality_flag_counts": _quality_flag_counts(result.frame),
                "applied_rules": list(result.applied_rules),
                "source_sha256": _sha256(source_path) if source_path else None,
                "output_sha256": _sha256(output_path),
            }
        )

    manifest: dict[str, Any] = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "raw_data_directory": str(raw_directory),
        "processed_data_directory": str(processed_directory),
        "report_directory": str(report_directory),
        "source_table_count": len(source_tables),
        "processed_table_count": len(cleaned_results),
        "validation_status_counts": {
            name: {
                str(status): int(count)
                for status, count in report["status"].value_counts().items()
            }
            for name, report in validation_reports.items()
        },
        "validation_report_files": VALIDATION_REPORT_FILES,
        "tables": table_records,
    }
    _write_json(manifest, report_directory / MANIFEST_FILE_NAME)
    return manifest

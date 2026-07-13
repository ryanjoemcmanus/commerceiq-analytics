"""Focused tests for the first-phase data-quality helpers."""

from pathlib import Path

import pandas as pd
import pytest

from src.data_cleaning import (
    audit_dataframe,
    discover_csv_files,
    find_timestamp_issues,
    identify_likely_primary_keys,
)


def test_discover_csv_files_is_case_insensitive_and_sorted(tmp_path: Path) -> None:
    """Discovery should recurse, ignore non-CSV files, and sort deterministically."""

    nested = tmp_path / "extracted_dataset"
    nested.mkdir()
    (tmp_path / "b.CSV").touch()
    (tmp_path / "a.csv").touch()
    (nested / "c.csv").touch()
    (tmp_path / "notes.txt").touch()

    assert [path.relative_to(tmp_path).as_posix() for path in discover_csv_files(tmp_path)] == [
        "a.csv",
        "b.CSV",
        "extracted_dataset/c.csv",
    ]


def test_identify_likely_primary_keys_requires_unique_non_null_ids() -> None:
    """Only ID-like columns meeting key constraints should be suggested."""

    frame = pd.DataFrame(
        {
            "order_id": ["a", "b", "c"],
            "customer_id": ["x", "x", "y"],
            "label": ["one", "two", "three"],
        }
    )

    assert identify_likely_primary_keys(frame) == ["order_id"]


def test_find_timestamp_issues_counts_only_unparseable_non_blanks() -> None:
    """Blank values should be missing, while invalid populated values are flagged."""

    frame = pd.DataFrame(
        {"order_purchase_timestamp": ["2018-01-01 10:00:00", "not-a-date", "", None]}
    )

    issues = find_timestamp_issues(frame)

    assert len(issues) == 1
    assert issues[0].non_null_values == 2
    assert issues[0].invalid_values == 1
    assert issues[0].invalid_examples == ("not-a-date",)


def test_audit_dataframe_reports_observed_quality_conditions() -> None:
    """The audit should calculate missingness and fully duplicated rows."""

    frame = pd.DataFrame({"value": [1.0, 1.0, None]})
    audit = audit_dataframe(frame, file_name="sample.csv")

    assert audit.row_count == 3
    assert audit.column_count == 1
    assert audit.duplicate_rows == 1
    assert audit.missing_values == {"value": 1}


def test_audit_dataframe_rejects_empty_file_label() -> None:
    """Reports need a meaningful source label."""

    with pytest.raises(ValueError, match="non-empty"):
        audit_dataframe(pd.DataFrame(), file_name=" ")

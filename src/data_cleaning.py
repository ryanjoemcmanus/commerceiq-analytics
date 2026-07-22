"""Reusable source-audit and conservative table-cleaning helpers.

All transformations operate on in-memory copies. Source CSV files are never
changed or overwritten.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Any, Iterable

import pandas as pd
from pandas.api.types import is_object_dtype, is_string_dtype


TIMESTAMP_NAME_PATTERN = re.compile(r"(?:date|time|timestamp|_at$)", re.IGNORECASE)
PRIMARY_KEY_NAME_PATTERN = re.compile(r"(?:^id$|_id$)", re.IGNORECASE)

TIMESTAMP_COLUMNS = {
    "olist_orders_dataset.csv": (
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ),
    "olist_order_items_dataset.csv": ("shipping_limit_date",),
    "olist_order_reviews_dataset.csv": (
        "review_creation_date",
        "review_answer_timestamp",
    ),
}

NUMERIC_COLUMNS = {
    "olist_customers_dataset.csv": ("customer_zip_code_prefix",),
    "olist_geolocation_dataset.csv": (
        "geolocation_zip_code_prefix",
        "geolocation_lat",
        "geolocation_lng",
    ),
    "olist_order_items_dataset.csv": (
        "order_item_id",
        "price",
        "freight_value",
    ),
    "olist_order_payments_dataset.csv": (
        "payment_sequential",
        "payment_installments",
        "payment_value",
    ),
    "olist_order_reviews_dataset.csv": ("review_score",),
    "olist_products_dataset.csv": (
        "product_name_lenght",
        "product_description_lenght",
        "product_photos_qty",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    ),
    "olist_sellers_dataset.csv": ("seller_zip_code_prefix",),
}


@dataclass(frozen=True)
class TimestampIssue:
    """Summary of values that cannot be parsed as timestamps."""

    column: str
    non_null_values: int
    invalid_values: int
    invalid_examples: tuple[str, ...]


@dataclass(frozen=True)
class TableAudit:
    """Structured quality-audit result for one CSV file."""

    file_name: str
    row_count: int
    column_count: int
    duplicate_rows: int
    column_names: tuple[str, ...]
    inferred_dtypes: dict[str, str]
    missing_values: dict[str, int]
    likely_primary_keys: tuple[str, ...]
    timestamp_issues: tuple[TimestampIssue, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a display-friendly dictionary representation."""

        result = asdict(self)
        result["timestamp_issues"] = [asdict(issue) for issue in self.timestamp_issues]
        return result


@dataclass(frozen=True)
class CleaningResult:
    """A cleaned table and the transformations applied to it."""

    frame: pd.DataFrame
    applied_rules: tuple[str, ...]


def discover_csv_files(raw_data_dir: Path | str) -> list[Path]:
    """Return CSV files below a raw-data directory, sorted by relative path.

    Recursive discovery accommodates archives that extract into a wrapper
    directory while preserving the raw files exactly as downloaded.

    Args:
        raw_data_dir: Directory expected to contain source CSV files.

    Raises:
        NotADirectoryError: If the supplied path is not an existing directory.
    """

    directory = Path(raw_data_dir).expanduser().resolve()
    if not directory.is_dir():
        raise NotADirectoryError(
            f"Raw data directory does not exist: {directory}. "
            "Create it and add the Olist CSV files."
        )
    return sorted(
        (
            path
            for path in directory.rglob("*")
            if path.is_file() and path.suffix.lower() == ".csv"
        ),
        key=lambda path: str(path.relative_to(directory)).lower(),
    )


def load_csv_safely(csv_path: Path | str, **read_csv_kwargs: Any) -> pd.DataFrame:
    """Load one CSV with contextual validation and error messages.

    pandas infers column types by default. Callers may pass supported
    ``pandas.read_csv`` keyword arguments when a source needs special handling.
    """

    path = Path(csv_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"CSV file was not found: {path}")
    if path.suffix.lower() != ".csv":
        raise ValueError(f"Expected a .csv file, received: {path.name}")

    options: dict[str, Any] = {"low_memory": False}
    options.update(read_csv_kwargs)
    try:
        return pd.read_csv(path, **options)
    except (OSError, UnicodeError, pd.errors.ParserError) as exc:
        raise ValueError(
            f"Could not read {path.name}. Confirm that it is an unmodified, "
            "valid CSV file and check its encoding and delimiter."
        ) from exc


def identify_likely_primary_keys(frame: pd.DataFrame) -> list[str]:
    """Identify non-null, unique columns whose names resemble identifiers.

    This is a heuristic, not a declaration of database constraints. Composite
    keys and business keys must be confirmed during relational modeling.
    """

    if frame.empty:
        return []

    candidates: list[str] = []
    for column in frame.columns:
        if not PRIMARY_KEY_NAME_PATTERN.search(str(column)):
            continue
        series = frame[column]
        if series.notna().all() and series.is_unique:
            candidates.append(str(column))
    return candidates


def find_timestamp_issues(
    frame: pd.DataFrame,
    *,
    example_limit: int = 5,
) -> list[TimestampIssue]:
    """Find non-null timestamp-like values that pandas cannot parse.

    Columns are selected conservatively by their names. The source frame is not
    modified, and blank strings are treated as missing rather than invalid.
    """

    if example_limit < 1:
        raise ValueError("example_limit must be at least 1.")

    issues: list[TimestampIssue] = []
    for column in frame.columns:
        if not TIMESTAMP_NAME_PATTERN.search(str(column)):
            continue
        series = frame[column]
        if not (is_object_dtype(series.dtype) or is_string_dtype(series.dtype)):
            continue

        normalized = series.astype("string").str.strip().replace("", pd.NA)
        non_null = normalized.dropna()
        if non_null.empty:
            continue

        parsed = pd.to_datetime(non_null, errors="coerce")
        invalid_mask = parsed.isna()
        invalid_count = int(invalid_mask.sum())
        examples = tuple(non_null[invalid_mask].drop_duplicates().head(example_limit).tolist())
        issues.append(
            TimestampIssue(
                column=str(column),
                non_null_values=int(non_null.shape[0]),
                invalid_values=invalid_count,
                invalid_examples=examples,
            )
        )
    return issues


def _build_warnings(
    frame: pd.DataFrame,
    duplicate_rows: int,
    timestamp_issues: Iterable[TimestampIssue],
    likely_primary_keys: list[str],
) -> list[str]:
    """Create concise, evidence-based warnings for a table audit."""

    warnings: list[str] = []
    if frame.empty:
        warnings.append("The file contains no data rows.")
    if duplicate_rows:
        warnings.append(f"Found {duplicate_rows:,} fully duplicated row(s).")

    columns_with_missing = int(frame.isna().any().sum())
    if columns_with_missing:
        warnings.append(f"Found missing values in {columns_with_missing:,} column(s).")

    invalid_timestamp_total = sum(issue.invalid_values for issue in timestamp_issues)
    if invalid_timestamp_total:
        warnings.append(
            f"Found {invalid_timestamp_total:,} unparseable value(s) in timestamp-like columns."
        )
    if not likely_primary_keys:
        warnings.append(
            "No single non-null, unique ID-like column was identified; verify the intended key grain."
        )
    return warnings


def audit_dataframe(frame: pd.DataFrame, *, file_name: str) -> TableAudit:
    """Calculate a structured quality audit for an in-memory DataFrame."""

    if not isinstance(frame, pd.DataFrame):
        raise TypeError("frame must be a pandas DataFrame.")
    if not file_name.strip():
        raise ValueError("file_name must be a non-empty label.")

    duplicate_rows = int(frame.duplicated().sum())
    likely_primary_keys = identify_likely_primary_keys(frame)
    timestamp_issues = find_timestamp_issues(frame)
    warnings = _build_warnings(
        frame,
        duplicate_rows,
        timestamp_issues,
        likely_primary_keys,
    )

    return TableAudit(
        file_name=file_name,
        row_count=int(frame.shape[0]),
        column_count=int(frame.shape[1]),
        duplicate_rows=duplicate_rows,
        column_names=tuple(str(column) for column in frame.columns),
        inferred_dtypes={str(column): str(dtype) for column, dtype in frame.dtypes.items()},
        missing_values={str(column): int(count) for column, count in frame.isna().sum().items()},
        likely_primary_keys=tuple(likely_primary_keys),
        timestamp_issues=tuple(timestamp_issues),
        warnings=tuple(warnings),
    )


def audit_csv_file(csv_path: Path | str, **read_csv_kwargs: Any) -> TableAudit:
    """Load and audit one CSV without changing the source file."""

    path = Path(csv_path)
    frame = load_csv_safely(path, **read_csv_kwargs)
    return audit_dataframe(frame, file_name=path.name)


def audit_csv_directory(raw_data_dir: Path | str) -> tuple[list[TableAudit], dict[str, str]]:
    """Audit every CSV in a directory while isolating per-file read failures.

    Returns:
        A pair containing successful table audits and a mapping of file names to
        clear error messages. One malformed file does not hide results for the
        remaining files.
    """

    audits: list[TableAudit] = []
    errors: dict[str, str] = {}
    for path in discover_csv_files(raw_data_dir):
        try:
            audits.append(audit_csv_file(path))
        except (FileNotFoundError, TypeError, ValueError) as exc:
            errors[path.name] = str(exc)
    return audits, errors


def build_overview_table(audits: Iterable[TableAudit]) -> pd.DataFrame:
    """Build a compact cross-file summary suitable for notebook display."""

    records = [
        {
            "file_name": audit.file_name,
            "rows": audit.row_count,
            "columns": audit.column_count,
            "duplicate_rows": audit.duplicate_rows,
            "columns_with_missing": sum(value > 0 for value in audit.missing_values.values()),
            "likely_primary_keys": ", ".join(audit.likely_primary_keys) or "None identified",
            "quality_warnings": len(audit.warnings),
        }
        for audit in audits
    ]
    return pd.DataFrame.from_records(records)


def _strip_text_values(frame: pd.DataFrame) -> pd.DataFrame:
    """Trim surrounding whitespace and standardize blank text as missing."""

    cleaned = frame.copy(deep=True)
    for column in cleaned.select_dtypes(include=["object", "string"]).columns:
        cleaned[column] = cleaned[column].astype("string").str.strip().replace("", pd.NA)
    return cleaned


def _coerce_numeric_columns(
    frame: pd.DataFrame,
    columns: Iterable[str],
    *,
    file_name: str,
) -> pd.DataFrame:
    """Convert declared numeric columns and reject newly introduced nulls."""

    cleaned = frame.copy(deep=True)
    for column in columns:
        if column not in cleaned.columns:
            raise ValueError(f"Expected numeric column {column!r} in {file_name}.")
        source_non_null = cleaned[column].notna()
        converted = pd.to_numeric(cleaned[column], errors="coerce")
        invalid_count = int((source_non_null & converted.isna()).sum())
        if invalid_count:
            raise ValueError(
                f"Column {column!r} in {file_name} contains {invalid_count} "
                "non-null value(s) that cannot be converted to numeric."
            )
        cleaned[column] = converted
    return cleaned


def _parse_timestamp_columns(
    frame: pd.DataFrame,
    columns: Iterable[str],
    *,
    file_name: str,
) -> pd.DataFrame:
    """Parse timestamps and add a flag for every unparseable populated value."""

    cleaned = frame.copy(deep=True)
    for column in columns:
        if column not in cleaned.columns:
            raise ValueError(f"Expected timestamp column {column!r} in {file_name}.")
        source_non_null = cleaned[column].notna()
        parsed = pd.to_datetime(cleaned[column], errors="coerce")
        cleaned[f"dq_invalid_{column}"] = source_non_null & parsed.isna()
        cleaned[column] = parsed
    return cleaned


def _add_order_timestamp_flags(frame: pd.DataFrame) -> pd.DataFrame:
    """Flag observed chronological exceptions without changing timestamps."""

    cleaned = frame.copy(deep=True)
    rules = {
        "dq_purchase_after_carrier_handoff": (
            "order_purchase_timestamp",
            "order_delivered_carrier_date",
        ),
        "dq_approval_after_carrier_handoff": (
            "order_approved_at",
            "order_delivered_carrier_date",
        ),
        "dq_carrier_handoff_after_customer_delivery": (
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
        ),
    }
    for flag, (earlier_column, later_column) in rules.items():
        comparable = cleaned[earlier_column].notna() & cleaned[later_column].notna()
        cleaned[flag] = comparable & (cleaned[earlier_column] > cleaned[later_column])
    cleaned["dq_has_timestamp_sequence_issue"] = cleaned[list(rules)].any(axis=1)
    return cleaned


def clean_source_table(
    frame: pd.DataFrame,
    *,
    file_name: str,
    category_translation: pd.DataFrame | None = None,
) -> CleaningResult:
    """Apply conservative, table-specific transformations to one source table.

    The function preserves row grain except for exact duplicate geolocation
    observations. Missing optional attributes and business-rule exceptions are
    retained rather than imputed or removed.
    """

    if not isinstance(frame, pd.DataFrame):
        raise TypeError("frame must be a pandas DataFrame.")
    if not file_name.strip():
        raise ValueError("file_name must be a non-empty label.")

    cleaned = _strip_text_values(frame)
    rules = ["trimmed surrounding text whitespace", "standardized blank text as missing"]

    if file_name in NUMERIC_COLUMNS:
        cleaned = _coerce_numeric_columns(
            cleaned,
            NUMERIC_COLUMNS[file_name],
            file_name=file_name,
        )
        rules.append("validated and converted declared numeric columns")

    if file_name in TIMESTAMP_COLUMNS:
        cleaned = _parse_timestamp_columns(
            cleaned,
            TIMESTAMP_COLUMNS[file_name],
            file_name=file_name,
        )
        rules.append("parsed declared timestamps and added invalid-value flags")

    if file_name == "olist_orders_dataset.csv":
        cleaned["order_status"] = cleaned["order_status"].str.lower()
        cleaned = _add_order_timestamp_flags(cleaned)
        rules.extend(
            [
                "normalized order_status to lowercase",
                "added non-destructive timestamp-sequence quality flags",
            ]
        )
    elif file_name == "olist_order_items_dataset.csv":
        cleaned["dq_negative_price"] = cleaned["price"].lt(0)
        cleaned["dq_negative_freight_value"] = cleaned["freight_value"].lt(0)
        rules.append("added non-negative monetary-value flags")
    elif file_name == "olist_order_payments_dataset.csv":
        cleaned["payment_type"] = cleaned["payment_type"].str.lower()
        cleaned["dq_negative_payment_value"] = cleaned["payment_value"].lt(0)
        cleaned["dq_negative_payment_installments"] = cleaned["payment_installments"].lt(0)
        rules.extend(
            [
                "normalized payment_type to lowercase",
                "added payment-domain quality flags",
            ]
        )
    elif file_name == "olist_order_reviews_dataset.csv":
        cleaned["dq_review_score_out_of_range"] = ~cleaned["review_score"].between(1, 5)
        rules.append("added review-score domain flag")
    elif file_name == "olist_products_dataset.csv":
        if category_translation is None:
            raise ValueError("category_translation is required when cleaning products.")
        translation = _strip_text_values(category_translation)
        category_map = translation.set_index("product_category_name")[
            "product_category_name_english"
        ]
        translated = cleaned["product_category_name"].map(category_map)
        cleaned["dq_category_missing"] = cleaned["product_category_name"].isna()
        cleaned["dq_category_translation_missing"] = (
            cleaned["product_category_name"].notna() & translated.isna()
        )
        cleaned["product_category_name_english"] = (
            translated.fillna(cleaned["product_category_name"]).fillna("unknown")
        )
        cleaned = cleaned.rename(
            columns={
                "product_name_lenght": "product_name_length",
                "product_description_lenght": "product_description_length",
            }
        )
        rules.extend(
            [
                "added English category with source-name and unknown fallbacks",
                "added missing-category and missing-translation flags",
                "corrected processed product length column spellings",
            ]
        )
    elif file_name == "olist_geolocation_dataset.csv":
        before = len(cleaned)
        cleaned = cleaned.drop_duplicates().reset_index(drop=True)
        rules.append(f"removed {before - len(cleaned)} exact duplicate observation(s)")

    return CleaningResult(frame=cleaned, applied_rules=tuple(rules))


def build_geolocation_lookup(
    cleaned_geolocation: pd.DataFrame,
    *,
    source_geolocation: pd.DataFrame,
) -> CleaningResult:
    """Create one deterministic representative location per ZIP-code prefix.

    Coordinates use the median of unique observations. City/state use the most
    frequent pair, with alphabetical tie-breaking for reproducibility.
    """

    required = {
        "geolocation_zip_code_prefix",
        "geolocation_lat",
        "geolocation_lng",
        "geolocation_city",
        "geolocation_state",
    }
    missing = sorted(required - set(cleaned_geolocation.columns))
    if missing:
        raise ValueError(f"Cannot build geolocation lookup; missing columns: {', '.join(missing)}")

    zip_column = "geolocation_zip_code_prefix"
    pair_counts = (
        cleaned_geolocation.groupby(
            [zip_column, "geolocation_city", "geolocation_state"],
            dropna=False,
        )
        .size()
        .rename("pair_observation_count")
        .reset_index()
        .sort_values(
            [zip_column, "pair_observation_count", "geolocation_state", "geolocation_city"],
            ascending=[True, False, True, True],
        )
    )
    representative = pair_counts.drop_duplicates(zip_column)[
        [zip_column, "geolocation_city", "geolocation_state"]
    ]
    aggregates = (
        cleaned_geolocation.groupby(zip_column)
        .agg(
            latitude=("geolocation_lat", "median"),
            longitude=("geolocation_lng", "median"),
            unique_observation_count=(zip_column, "size"),
            city_variant_count=("geolocation_city", "nunique"),
            state_variant_count=("geolocation_state", "nunique"),
        )
        .reset_index()
    )
    lookup = aggregates.merge(representative, on=zip_column, validate="one_to_one")
    lookup = lookup.rename(
        columns={
            zip_column: "zip_code_prefix",
            "geolocation_city": "city",
            "geolocation_state": "state",
        }
    )

    if zip_column not in source_geolocation.columns:
        raise ValueError(f"Source geolocation is missing required column: {zip_column}")
    source_counts = source_geolocation.groupby(zip_column).size()
    lookup["source_observation_count"] = lookup["zip_code_prefix"].map(source_counts)
    lookup["dq_multiple_state_codes"] = lookup["state_variant_count"].gt(1)
    return CleaningResult(
        frame=lookup.sort_values("zip_code_prefix").reset_index(drop=True),
        applied_rules=(
            "aggregated to one row per ZIP-code prefix",
            "used median coordinates from unique observations",
            "selected most frequent city/state pair with deterministic tie-breaking",
            "added source-observation and geographic-variant quality counts",
        ),
    )

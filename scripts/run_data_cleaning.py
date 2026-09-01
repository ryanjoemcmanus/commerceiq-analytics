"""Generate cleaned CommerceIQ tables from immutable Olist source CSVs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cleaning_pipeline import run_cleaning_pipeline  # noqa: E402
from src.config import PROCESSED_DATA_DIR, RAW_DATA_DIR, REPORTS_DIR  # noqa: E402


def parse_arguments() -> argparse.Namespace:
    """Parse optional source, destination, and report path overrides."""

    parser = argparse.ArgumentParser(
        description="Create validated processed Olist tables without changing raw files."
    )
    parser.add_argument("--raw-data-dir", type=Path, default=RAW_DATA_DIR)
    parser.add_argument("--processed-data-dir", type=Path, default=PROCESSED_DATA_DIR)
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=REPORTS_DIR / "data_cleaning",
    )
    return parser.parse_args()


def main() -> int:
    """Run cleaning and return a shell-friendly status code."""

    arguments = parse_arguments()
    try:
        manifest = run_cleaning_pipeline(
            arguments.raw_data_dir,
            arguments.processed_data_dir,
            arguments.report_dir,
        )
    except (FileNotFoundError, NotADirectoryError, OSError, TypeError, ValueError) as exc:
        print(f"Cleaning failed: {exc}", file=sys.stderr)
        return 1

    print(
        "Cleaning complete: "
        f"{manifest['source_table_count']} source table(s) produced "
        f"{manifest['processed_table_count']} processed table(s)."
    )
    print(f"Processed data: {manifest['processed_data_directory']}")
    print(f"Manifest and validation: {manifest['report_directory']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


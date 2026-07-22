"""Validate or load CommerceIQ processed data into PostgreSQL."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    DatabaseSettings,
    PROCESSED_DATA_DIR,
    REPORTS_DIR,
)
from src.database_loader import (  # noqa: E402
    create_database_engine,
    load_processed_data,
    split_sql_statements,
    validate_processed_files,
)


def parse_arguments() -> argparse.Namespace:
    """Parse database-load and dry-run options."""

    parser = argparse.ArgumentParser(
        description="Validate processed files or load them transactionally into PostgreSQL."
    )
    parser.add_argument("--processed-data-dir", type=Path, default=PROCESSED_DATA_DIR)
    parser.add_argument("--dry-run", action="store_true", help="Validate files and SQL without connecting.")
    parser.add_argument(
        "--recreate-schema",
        action="store_true",
        help="Drop and recreate the managed schema before loading.",
    )
    parser.add_argument("--chunksize", type=int, default=5_000)
    return parser.parse_args()


def _write_reports(load_counts, quality_checks) -> Path:
    """Persist non-sensitive database load evidence."""

    report_directory = REPORTS_DIR / "database"
    report_directory.mkdir(parents=True, exist_ok=True)
    load_counts.to_csv(report_directory / "database_load_counts.csv", index=False)
    quality_checks.to_csv(report_directory / "database_quality_checks.csv", index=False)
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "loaded_table_count": int(len(load_counts)),
        "quality_check_count": int(len(quality_checks)),
        "failed_quality_check_count": int(quality_checks["status"].eq("failed").sum()),
    }
    (report_directory / "database_load_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return report_directory


def main() -> int:
    """Validate inputs or execute the PostgreSQL load."""

    arguments = parse_arguments()
    schema_path = PROJECT_ROOT / "sql" / "schema.sql"
    quality_path = PROJECT_ROOT / "sql" / "data_quality_checks.sql"
    try:
        validation = validate_processed_files(arguments.processed_data_dir)
        split_sql_statements(schema_path.read_text(encoding="utf-8"))
        if not quality_path.read_text(encoding="utf-8").strip():
            raise ValueError("Database quality-check SQL is empty.")
        if arguments.dry_run:
            print(validation.to_string(index=False))
            print("Dry run complete: processed files and SQL assets are valid.")
            return 0

        settings = DatabaseSettings.from_environment()
        engine = create_database_engine(settings)
        try:
            load_counts, quality_checks = load_processed_data(
                engine,
                arguments.processed_data_dir,
                schema_path,
                quality_path,
                recreate_schema=arguments.recreate_schema,
                chunksize=arguments.chunksize,
            )
        finally:
            engine.dispose()
        report_directory = _write_reports(load_counts, quality_checks)
    except (FileNotFoundError, OSError, TypeError, ValueError) as exc:
        print(f"Database load failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(
            "Database connection or load failed. Confirm PostgreSQL is running and "
            f"the .env settings are correct. Details: {exc}",
            file=sys.stderr,
        )
        return 1

    print(f"Database load complete. Reports: {report_directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


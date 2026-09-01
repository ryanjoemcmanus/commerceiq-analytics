"""Run the CommerceIQ read-only source-data audit from the command line."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import RAW_DATA_DIR, REPORTS_DIR  # noqa: E402
from src.data_quality import run_data_quality_audit  # noqa: E402


def parse_arguments() -> argparse.Namespace:
    """Parse optional path overrides for local or automated runs."""

    parser = argparse.ArgumentParser(
        description=(
            "Audit source CSV files without modifying them and export structured reports."
        )
    )
    parser.add_argument(
        "--raw-data-dir",
        type=Path,
        default=RAW_DATA_DIR,
        help=f"CSV source directory (default: {RAW_DATA_DIR})",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=REPORTS_DIR / "data_quality",
        help=f"Audit output directory (default: {REPORTS_DIR / 'data_quality'})",
    )
    return parser.parse_args()


def main() -> int:
    """Run the audit and return a process exit code."""

    arguments = parse_arguments()
    try:
        summary = run_data_quality_audit(arguments.raw_data_dir, arguments.report_dir)
    except (FileNotFoundError, NotADirectoryError, OSError, ValueError) as exc:
        print(f"Audit failed: {exc}", file=sys.stderr)
        return 1

    print(
        "Audit complete: "
        f"{summary['audited_file_count']} file(s) audited, "
        f"{summary['load_error_count']} load error(s)."
    )
    print(f"Reports: {Path(summary['report_directory'])}")
    return 1 if summary["load_error_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())


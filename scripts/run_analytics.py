"""Execute CommerceIQ KPI and advanced-analysis SQL against PostgreSQL."""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analytics_pipeline import run_analytics_pipeline  # noqa: E402
from src.config import DatabaseSettings, REPORTS_DIR  # noqa: E402
from src.database_loader import create_database_engine  # noqa: E402


def main() -> int:
    """Run all documented analytics and export their result tables."""

    sql_paths = (
        PROJECT_ROOT / "sql" / "kpi_queries.sql",
        PROJECT_ROOT / "sql" / "advanced_analysis.sql",
    )
    output_directory = REPORTS_DIR / "analytics"
    try:
        settings = DatabaseSettings.from_environment()
        engine = create_database_engine(settings)
        try:
            manifest = run_analytics_pipeline(engine, sql_paths, output_directory)
        finally:
            engine.dispose()
    except Exception as exc:
        print(f"Analytics pipeline failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"Analytics complete: {manifest['query_count']} query result(s) written to "
        f"{output_directory}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


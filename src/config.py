"""Project configuration sourced from paths and environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"


@dataclass(frozen=True)
class DatabaseSettings:
    """PostgreSQL connection settings loaded from the local environment."""

    host: str
    port: int
    name: str
    user: str
    password: str

    @classmethod
    def from_environment(cls) -> DatabaseSettings:
        """Build validated database settings from environment variables.

        Raises:
            ValueError: If a required variable is absent or DB_PORT is invalid.
        """

        variable_names = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")
        values = {name: os.getenv(name) for name in variable_names}
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise ValueError(
                "Missing required database environment variables: "
                f"{', '.join(missing)}. Copy .env.example to .env and set local values."
            )

        try:
            port = int(values["DB_PORT"] or "")
        except ValueError as exc:
            raise ValueError("DB_PORT must be a valid integer.") from exc

        if not 1 <= port <= 65535:
            raise ValueError("DB_PORT must be between 1 and 65535.")

        return cls(
            host=values["DB_HOST"] or "",
            port=port,
            name=values["DB_NAME"] or "",
            user=values["DB_USER"] or "",
            password=values["DB_PASSWORD"] or "",
        )

    @property
    def sqlalchemy_url(self) -> str:
        """Return a SQLAlchemy URL with safely escaped credentials."""

        user = quote_plus(self.user)
        password = quote_plus(self.password)
        host = self.host.strip()
        database = quote_plus(self.name)
        return f"postgresql+psycopg://{user}:{password}@{host}:{self.port}/{database}"


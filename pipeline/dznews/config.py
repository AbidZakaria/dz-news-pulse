"""Runtime configuration, read from environment variables (12-factor style)."""

import os
from pathlib import Path

# <repo>/pipeline/dznews/config.py -> <repo>. The same relative layout holds inside the
# Airflow container (/opt/airflow/pipeline/dznews/...), so the dbt seed path works in both.
ROOT = Path(__file__).resolve().parents[2]
SOURCES_CSV = Path(os.getenv("SOURCES_CSV", ROOT / "dbt" / "seeds" / "news_sources.csv"))
SQL_DIR = Path(__file__).resolve().parent / "sql"
SAMPLE_DIR = ROOT / "sample_data"

USER_AGENT = "Mozilla/5.0 (compatible; dz-news-pulse/1.0; portfolio data-engineering project)"
HTTP_TIMEOUT_SECONDS = int(os.getenv("HTTP_TIMEOUT_SECONDS", "20"))


def warehouse_dsn() -> dict:
    """Connection settings for the analytics warehouse (PostgreSQL)."""
    return {
        "host": os.getenv("WAREHOUSE_HOST", "localhost"),
        "port": int(os.getenv("WAREHOUSE_PORT", "5433")),
        "dbname": os.getenv("WAREHOUSE_DB", "news"),
        "user": os.getenv("WAREHOUSE_USER", "news"),
        "password": os.getenv("WAREHOUSE_PASSWORD", "news"),
    }

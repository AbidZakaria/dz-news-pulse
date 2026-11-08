"""Load: write cleaned articles into the raw schema of the warehouse."""

import psycopg2
from psycopg2.extras import execute_values

from dznews import config
from dznews.transform import COLUMNS

_INSERT_SQL = f"""
    INSERT INTO raw.articles ({", ".join(COLUMNS)})
    VALUES %s
    ON CONFLICT (article_id) DO NOTHING
    RETURNING article_id
"""


def get_connection():
    return psycopg2.connect(**config.warehouse_dsn(), connect_timeout=10)


def ensure_schema(conn) -> None:
    """Create the raw schema/tables if needed (idempotent)."""
    with conn.cursor() as cur:
        cur.execute((config.SQL_DIR / "init.sql").read_text(encoding="utf-8"))
    conn.commit()


def insert_articles(conn, df) -> int:
    """Insert new articles; already-known ones are skipped. Returns rows really inserted.

    ON CONFLICT DO NOTHING makes every run idempotent: re-running a failed DAG run,
    or scraping the same feed twice, never creates duplicates.
    """
    if df.empty:
        return 0
    clean = df[COLUMNS].astype(object).where(df[COLUMNS].notna(), None)
    rows = list(clean.itertuples(index=False, name=None))
    with conn.cursor() as cur:
        inserted = execute_values(cur, _INSERT_SQL, rows, fetch=True)
    conn.commit()
    return len(inserted)


def log_run(
    conn,
    batch_id: str,
    source_id: str,
    status: str,
    fetched: int = 0,
    rejected: int = 0,
    inserted: int = 0,
    error: str | None = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO raw.ingestion_log
                (batch_id, source_id, status, fetched_count, rejected_count, inserted_count, error)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (batch_id, source_id, status, fetched, rejected, inserted, error),
        )
    conn.commit()

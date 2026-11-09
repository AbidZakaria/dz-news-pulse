"""Load: write cleaned articles into the raw schema of the warehouse."""

import psycopg2
from psycopg2.extras import execute_values

from dznews import config, migrate
from dznews.transform import COLUMNS

# New articles are inserted. Known ones are left alone, except that data we did not
# capture the first time (full text, tags, lead image) is filled in. (xmax = 0) is true only for
# rows that were really inserted, so the returned flags count genuinely new articles.
_INSERT_SQL = f"""
    INSERT INTO raw.articles ({", ".join(COLUMNS)})
    VALUES %s
    ON CONFLICT (article_id) DO UPDATE SET
        content    = COALESCE(raw.articles.content, EXCLUDED.content),
        categories = COALESCE(raw.articles.categories, EXCLUDED.categories),
        image_url  = COALESCE(raw.articles.image_url, EXCLUDED.image_url)
    RETURNING (xmax = 0) AS inserted
"""


def get_connection():
    return psycopg2.connect(**config.warehouse_dsn(), connect_timeout=10)


def ensure_schema(conn) -> list[str]:
    """Bring the warehouse schema up to date (idempotent). Returns migrations applied."""
    return migrate.apply_pending(conn)


def insert_articles(conn, df) -> int:
    """Insert new articles; already-known ones are not duplicated. Returns rows inserted.

    The conflict clause makes every run idempotent: re-running a failed DAG run, or
    scraping the same feed twice, never creates duplicates.
    """
    if df.empty:
        return 0
    clean = df[COLUMNS].astype(object).where(df[COLUMNS].notna(), None)
    rows = list(clean.itertuples(index=False, name=None))
    with conn.cursor() as cur:
        results = execute_values(cur, _INSERT_SQL, rows, fetch=True)
    conn.commit()
    return sum(1 for (was_inserted,) in results if was_inserted)


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

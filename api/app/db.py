"""Tiny PostgreSQL helper: the API only ever READS the marts schema."""

import os

import psycopg2
from psycopg2.extras import RealDictCursor


def _dsn() -> dict:
    return {
        "host": os.getenv("WAREHOUSE_HOST", "localhost"),
        "port": int(os.getenv("WAREHOUSE_PORT", "5433")),
        "dbname": os.getenv("WAREHOUSE_DB", "news"),
        "user": os.getenv("WAREHOUSE_USER", "news"),
        "password": os.getenv("WAREHOUSE_PASSWORD", "news"),
    }


def query(sql: str, params: dict | None = None) -> list[dict]:
    """Run a read-only query and return rows as dicts.

    A connection per request is plenty for this traffic; swap in a pool
    (psycopg_pool / pgbouncer) before putting real load on it.
    """
    conn = psycopg2.connect(**_dsn(), connect_timeout=5)
    try:
        conn.set_session(readonly=True, autocommit=True)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params or {})
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

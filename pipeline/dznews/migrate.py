"""Minimal, dependable schema migrations.

Files named V<number>__<description>.sql in dznews/migrations/ are applied once, in
order, each inside its own transaction, and recorded in public.schema_migrations.
Re-running is a no-op, so it is safe to call at every pipeline start and API boot.
"""

import logging
import re

from dznews import config

log = logging.getLogger(__name__)
_NAME_RE = re.compile(r"^V(\d+)__.+\.sql$")


def available() -> list[tuple[int, str]]:
    found = []
    for path in config.MIGRATIONS_DIR.glob("V*__*.sql"):
        match = _NAME_RE.match(path.name)
        if match:
            found.append((int(match.group(1)), path.name))
    return sorted(found)


def apply_pending(conn) -> list[str]:
    """Apply every migration not yet recorded. Returns the names that were applied."""
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.schema_migrations (
                version    integer PRIMARY KEY,
                name       text        NOT NULL,
                applied_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        # Serialise concurrent callers (several Airflow tasks start at once).
        cur.execute("SELECT pg_advisory_xact_lock(727001)")
        cur.execute("SELECT version FROM public.schema_migrations")
        done = {row[0] for row in cur.fetchall()}
    conn.commit()

    applied = []
    for version, name in available():
        if version in done:
            continue
        sql = (config.MIGRATIONS_DIR / name).read_text(encoding="utf-8")
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_xact_lock(727001)")
                cur.execute("SELECT 1 FROM public.schema_migrations WHERE version = %s", (version,))
                if cur.fetchone():  # another process applied it while we waited for the lock
                    conn.commit()
                    continue
                cur.execute(sql)
                cur.execute(
                    "INSERT INTO public.schema_migrations (version, name) VALUES (%s, %s)",
                    (version, name),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            log.exception("Migration %s failed and was rolled back", name)
            raise
        log.info("Applied migration %s", name)
        applied.append(name)
    return applied

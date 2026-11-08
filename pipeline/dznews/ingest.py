"""Ingestion of one source: extract -> transform -> load. Called by the Airflow DAG."""

import logging
import uuid
from datetime import UTC, datetime

from dznews import extract, load, sources, transform

log = logging.getLogger(__name__)


def ingest_source(source_id: str, batch_id: str | None = None) -> dict:
    """Fetch one feed and land its new articles in raw.articles.

    Failures are written to raw.ingestion_log and then re-raised, so Airflow can retry
    the task and alert - while the audit trail stays complete.
    """
    source = sources.get_source(source_id)
    batch_id = batch_id or uuid.uuid4().hex[:12]
    fetched_at = datetime.now(UTC)

    conn = load.get_connection()
    try:
        load.ensure_schema(conn)
        try:
            records = extract.parse_feed(extract.fetch_feed(source.feed_url))
            df, rejected = transform.build_articles_frame(records, source, batch_id, fetched_at)
            inserted = load.insert_articles(conn, df)
        except Exception as exc:
            conn.rollback()
            load.log_run(conn, batch_id, source_id, "failed", error=str(exc)[:500])
            raise

        load.log_run(
            conn, batch_id, source_id, "success",
            fetched=len(records), rejected=rejected, inserted=inserted,
        )
        result = {
            "source_id": source_id,
            "fetched": len(records),
            "rejected": rejected,
            "inserted": inserted,
        }
        log.info("Ingested %s", result)
        return result
    finally:
        conn.close()

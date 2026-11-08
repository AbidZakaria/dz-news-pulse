"""Data-quality gate that runs at the end of every DAG run (after dbt tests)."""


class DataQualityError(Exception):
    """Raised when the warehouse looks unhealthy after a run."""


def run_checks(conn, window_hours: int = 24, min_sources_ok: int = 2) -> list[str]:
    """Return a list of human-readable problems (empty list = healthy)."""
    problems: list[str] = []
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT count(DISTINCT source_id) FILTER (WHERE status = 'success'),
                   coalesce(sum(inserted_count), 0)
            FROM raw.ingestion_log
            WHERE finished_at > now() - make_interval(hours => %s)
            """,
            (window_hours,),
        )
        sources_ok, inserted = cur.fetchone()
        if sources_ok < min_sources_ok:
            problems.append(
                f"Only {sources_ok} source(s) ingested successfully in the last "
                f"{window_hours}h (minimum: {min_sources_ok})."
            )
        if inserted == 0:
            problems.append(f"No new articles were inserted in the last {window_hours}h.")

        cur.execute(
            "SELECT count(*) FROM raw.articles WHERE published_at > now() + interval '2 days'"
        )
        (future,) = cur.fetchone()
        if future:
            problems.append(f"{future} article(s) have a publication date in the future.")
    return problems


def assert_healthy(conn, **kwargs) -> None:
    problems = run_checks(conn, **kwargs)
    if problems:
        raise DataQualityError(" | ".join(problems))

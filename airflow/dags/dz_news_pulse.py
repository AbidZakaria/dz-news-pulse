"""
### DZ News Pulse - batch ELT pipeline

Every 6 hours: pull Algerian news from 7 RSS feeds (French + Arabic), land them raw in
PostgreSQL, let **dbt** turn them into a tested star schema (topics, keywords, facts),
then run a final data-quality gate.

    init_warehouse -> ingest_source (x7, one per site) -> enrich_articles
        -> dbt_seed -> dbt_run -> dbt_test -> quality_gate

`enrich_articles` is the intelligence step: local multilingual embeddings, then grouping
of articles about the same event into stories. It is incremental (only new articles).

Why every 6 hours? RSS feeds only expose the latest ~20-50 articles, so polling several
times a day is what builds up a complete history. The load is idempotent (see load.py).
"""

from datetime import datetime, timedelta

from airflow.decorators import dag, task
from airflow.operators.bash import BashOperator
from airflow.utils.trigger_rule import TriggerRule

from dznews import alerts, ingest, load, quality, sources

DBT = "/home/airflow/dbt-venv/bin/dbt"
NLP_PYTHON = "/home/airflow/nlp-venv/bin/python"  # has the embedding model's dependencies
DBT_DIR = "/opt/airflow/dbt"  # profiles.yml + env vars (DBT_PROFILES_DIR etc.) come from compose


def dbt_command(command: str) -> str:
    return f"cd {DBT_DIR} && {DBT} {command} --no-use-colors"


default_args = {
    "owner": "data-engineering",
    # Scheduled-failure handling: 3 retries with exponential back-off, then alert.
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=15),
    "on_failure_callback": alerts.notify_failure,
}


@dag(
    dag_id="dz_news_pulse",
    description="Algerian news -> PostgreSQL -> dbt star schema -> API",
    schedule="0 */6 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,  # RSS has no history, so back-filling past runs would be pointless
    max_active_runs=1,
    default_args=default_args,
    tags=["news", "elt", "dbt"],
    doc_md=__doc__,
)
def dz_news_pulse():
    @task
    def init_warehouse() -> None:
        """Create the raw schema/tables if they do not exist yet."""
        conn = load.get_connection()
        try:
            load.ensure_schema(conn)
        finally:
            conn.close()

    @task
    def ingest_source(source_id: str) -> dict:
        """Extract + clean + load ONE source. Mapped over every site (parallel, isolated)."""
        return ingest.ingest_source(source_id)

    # Embeddings + story clustering: incremental, CPU only, isolated in its own virtualenv.
    # ALL_DONE so that one failed source never blocks the enrichment of the others.
    enrich_articles = BashOperator(
        task_id="enrich_articles",
        bash_command=f"cd /opt/airflow/pipeline && {NLP_PYTHON} -m dznews.cli enrich",
        trigger_rule=TriggerRule.ALL_DONE,
        execution_timeout=timedelta(minutes=30),
    )

    # ALL_DONE: a broken news site must not block the other sources from being modelled.
    # (If the warehouse itself is down, dbt fails loudly right here.)
    dbt_seed = BashOperator(
        task_id="dbt_seed",
        bash_command=dbt_command("seed"),
        trigger_rule=TriggerRule.ALL_DONE,
    )
    dbt_run = BashOperator(task_id="dbt_run", bash_command=dbt_command("run"))
    dbt_test = BashOperator(task_id="dbt_test", bash_command=dbt_command("test"))

    @task
    def quality_gate() -> None:
        """Fail the run if too few sources worked or nothing new arrived."""
        conn = load.get_connection()
        try:
            quality.assert_healthy(conn)
        finally:
            conn.close()

    ingested = ingest_source.expand(source_id=[s.source_id for s in sources.load_sources()])
    init_warehouse() >> ingested >> enrich_articles
    # dbt must run even if enrichment failed: analytics on the raw data stay available.
    [ingested, enrich_articles] >> dbt_seed >> dbt_run >> dbt_test >> quality_gate()


dz_news_pulse()

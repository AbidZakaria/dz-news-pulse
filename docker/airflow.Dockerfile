FROM apache/airflow:2.10.5-python3.12

USER airflow

# dbt lives in its own virtualenv so its dependencies never clash with Airflow's.
RUN python -m venv /home/airflow/dbt-venv \
 && /home/airflow/dbt-venv/bin/pip install --no-cache-dir dbt-core==1.12.6 dbt-postgres==1.9.0

# The NLP stage (embeddings) gets its own virtualenv too: its dependencies (onnxruntime,
# numpy, ...) must never upgrade packages that Airflow itself pins.
COPY pipeline/requirements.txt /tmp/pipeline-requirements.txt
RUN python -m venv /home/airflow/nlp-venv  && /home/airflow/nlp-venv/bin/pip install --no-cache-dir -r /tmp/pipeline-requirements.txt

# Writable cache for the embedding model (mounted as a volume at runtime)
RUN mkdir -p /opt/airflow/model-cache

# Airflow's own environment only needs what the ingestion tasks import
RUN pip install --no-cache-dir feedparser==6.0.11

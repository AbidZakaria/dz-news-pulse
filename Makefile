.PHONY: up down logs test lint sample dbt-docs

up:            ## Start the whole stack (Airflow, warehouse, API)
	docker compose up --build -d

down:          ## Stop everything (add -v to also delete the data volumes)
	docker compose down

logs:
	docker compose logs -f airflow-scheduler

test:          ## Unit tests (no Docker needed)
	pip install -q -r requirements-dev.txt
	pytest -q

lint:
	ruff check .

sample:        ## Load offline demo data and build the marts (needs the warehouse running)
	PYTHONPATH=pipeline python -m dznews.cli load-sample
	cd dbt && dbt seed --profiles-dir . && dbt run --profiles-dir . && dbt test --profiles-dir .

dbt-docs:      ## Browse the dbt lineage graph at http://localhost:8081
	cd dbt && dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir . --port 8081

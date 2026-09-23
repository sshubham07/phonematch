.PHONY: up down db-shell migrate api ui test lint fmt nightly

up:
	docker compose up -d --wait

down:
	docker compose down

db-shell:
	docker compose exec db sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

migrate:
	uv run alembic upgrade head

api:
	uv run uvicorn app.main:app --reload

ui:
	uv run streamlit run ui/streamlit_app.py

test:
	uv run pytest -q

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy app jobs config

fmt:
	uv run ruff format .
	uv run ruff check --fix .

nightly:
	bash scripts/run_nightly.sh

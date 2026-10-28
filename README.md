# YourHealth

Family health report tracker: lab report trends, medicine-to-lab links, Hindi explanations, and doctor share sheets.

## Run locally

```bash
docker compose up -d postgres          # Postgres 16 + pgvector, creates yourhealth and yourhealth_test DBs
cd backend
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp ../.env.example .env
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

## Tests

```bash
cd backend
.venv/bin/pytest
```

Tests use the separate `yourhealth_test` database and need the Postgres container running.

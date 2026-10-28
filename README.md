# YourHealth

Family health report tracker: lab report trends, medicine-to-lab links, Hindi explanations, and doctor share sheets.

## Run locally

```bash
docker compose up -d postgres redis s3 # Postgres 16 + pgvector (yourhealth + yourhealth_test DBs), Redis queue, S3 store
cd backend
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp ../.env.example .env
sed -i "s|^JWT_SECRET=.*|JWT_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')|" .env
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

## Tests

```bash
cd backend
.venv/bin/pytest
```

Tests use the separate `yourhealth_test` database and need the `postgres`, `redis` and `s3` containers running.

File storage is any S3-compatible service. Locally that is SeaweedFS (MinIO no longer publishes public Docker images); set `S3_ENDPOINT` and keys in `.env` to point at real S3 in deployment.

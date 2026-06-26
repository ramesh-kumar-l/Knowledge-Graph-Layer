# Knowledge Graph Layer — Newbie Quick Starter Guide

## What is this project?
This repository is the SCP Knowledge Graph Layer. It is a backend service that ingests memory records, extracts entities and relationships, stores them in a versioned knowledge graph, and exposes a FastAPI HTTP API for graph queries, trust analysis, and conflict resolution.

The project includes:
- `src/` — main Python application source code
- `scripts/` — utility scripts for benchmarks and OpenAPI export
- `migrations/` — Alembic migration configuration and schema history
- `tests/` — unit and integration tests
- `sdk/` — Python SDK for the API
- `examples/` — runnable example of ingestion and querying
- `docs/` — runbook and API docs

## What do I need to run it?
### Required
- Python 3.11 or 3.12
- PostgreSQL database for normal runtime
- Optional: Redis for shared cache and rate limiting in multi-worker deployments

> Windows users: this repository is tested with Python 3.11 / 3.12. Python 3.14 may fail during dependency installation because native extensions like `asyncpg` and `pydantic-core` do not yet publish compatible wheels for that interpreter.

> Windows users: this repository is tested with Python 3.11 / 3.12. Python 3.14 can fail during dependency install because native extension packages like `asyncpg` and `pydantic-core` do not yet publish compatible wheels for that interpreter version.

### Recommended local dev extras
- `pip` or `python -m pip`
- `virtualenv` or `venv`
- `make` / task runner (optional)

## Install dependencies
From the repository root:
```bash
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If you want only the core runtime packages, install the top block of `requirements.txt`.

### Optional extras
- Redis support: `redis[asyncio]==5.0.0`
- OpenTelemetry tracing: `opentelemetry-api==1.24.0`, `opentelemetry-sdk==1.24.0`, `opentelemetry-instrumentation-fastapi==0.45b0`, `opentelemetry-exporter-otlp-proto-http==1.24.0`
- Local SQLite test support: `aiosqlite==0.20.0`

## How do I configure the app?
Copy `.env.example` to `.env` and edit values:
```bash
copy .env.example .env
```

Important environment variables:
- `DATABASE_URL` — PostgreSQL connection string, e.g. `postgresql+asyncpg://postgres:password@localhost:5432/scp_kg`
- `SYNC_DATABASE_URL` — optional sync URL used by Alembic migrations, e.g. `postgresql+psycopg2://postgres:password@localhost:5432/scp_kg`
- `TEST_DATABASE_URL` — used by tests, default is `sqlite+aiosqlite:///:memory:` in `.env.example`
- `APP_ENV` — environment name, typically `development`
- `LOG_LEVEL` — logging level, e.g. `INFO` or `DEBUG`
- `API_KEYS` — comma-separated API keys; omit or leave empty to disable auth in development
- `REDIS_URL` — Redis connection string when using shared cache/rate limiting
- `CORS_ORIGINS` — comma-separated allowed browser origins
- `OTEL_SERVICE_NAME` — optional OpenTelemetry service name
- `OTEL_EXPORTER_OTLP_ENDPOINT` — optional OTLP collector endpoint for traces

## How do I start the server?
Run this from the project root:
```bash
.\.venv\Scripts\activate
uvicorn src.api.main:app --reload --port 8000
```

For production or multi-worker use:
```bash
set API_KEYS=sk-prod
set DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/scp_kg
set REDIS_URL=redis://localhost:6379/0
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The health endpoint is:
```bash
curl http://localhost:8000/health
```
Expected response:
```json
{"status":"ok","version":"0.7.0"}
```

## What does the service expose?
The API is mounted under `/v1` and includes routers for:
- `entities` — entity CRUD, search, and version history
- `relationships` — relationship CRUD
- `evidence` — evidence management
- `ingestion` — ingest memory records into the graph
- `query` — graph traversal, neighbors, and path discovery
- `explain` — trust score breakdown and provenance
- `conflict` — dispute queue and resolution

Plus system endpoints:
- `/health` — service health status
- `/v1/openapi.json` — OpenAPI spec for the API

## How does auth work?
Auth is controlled by `API_KEYS`.
- If `API_KEYS` is not set or empty: auth is disabled and all routes are accessible.
- If `API_KEYS` is set: requests must include `X-Api-Key` with one valid key.

Example header:
```bash
-H "X-Api-Key: sk-demo"
```

## How does rate limiting work?
`src/api/rate_limit_redis.py` enforces the rate limit.
- Default limit: `100 requests / 60 seconds`
- When `REDIS_URL` is set: shared Redis sliding window across workers
- When `REDIS_URL` is unset: in-process fallback rate limiter is used
- Exceeded requests return `429 Too Many Requests` and `Retry-After: 60`

## How does caching work?
`src/api/cache.py` caches successful GET responses for graph and explain endpoints.
- Cache TTL: 60 seconds
- Cached endpoints: `/graph`, `/neighbors`, `/path/*`, and `/v1/explain/*`
- With `REDIS_URL` set: cache is shared across workers
- Without Redis: cache is process-local

API responses include `X-Cache: HIT` or `X-Cache: MISS`.

## How do I run database migrations?
The project uses Alembic with `migrations/env.py`.

Run migrations:
```bash
alembic upgrade head
```

Rollback one migration:
```bash
alembic downgrade -1
```

If Alembic needs a sync DB URL, set `SYNC_DATABASE_URL`.

## How do I run tests?
Execute:
```bash
pytest --cov=src
```

The repository includes unit and integration tests under `tests/unit` and `tests/integration`.

## How do I use the SDK and example?
The SDK package is in `sdk/knowledge_graph`.

Run the example:
```bash
python examples/ingest_and_query.py
```

The example requires the backend to be running at `http://localhost:8000`.
If `API_KEYS` is configured, set `API_KEY` inside the example or export it first.

## What are the main source directories?
- `src/api/` — FastAPI app, routers, middleware, auth, caching, tracing
- `src/adapters/postgres/` — async database engine, session, and ORM models
- `src/domain/` — Pydantic and domain model definitions
- `src/ingestion/` — memory ingestion pipeline, entity/relationship extraction, validation
- `src/repositories/` — persistence logic for entities, evidence, relationships, versions
- `src/services/` — business logic such as trust scoring, graph traversal, conflict resolution

## How is configuration loaded?
- `dotenv` loads `.env` values at startup from `src/adapters/postgres/connection.py` and `migrations/env.py`
- `DATABASE_URL` is loaded by `src/adapters/postgres/connection.py`
- `CORS_ORIGINS` defaults to `http://localhost:5173,http://localhost:4173`

## What if I want tracing?
Tracing is optional. If installed and configured, the app uses OpenTelemetry without failing when packages are missing.

Install the extras and set:
```bash
set OTEL_SERVICE_NAME=scp-knowledge-graph
set OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
```

If the OTel packages are absent, the service still runs with tracing disabled.

## What if I want Redis?
Set `REDIS_URL` to enable shared cache and rate limiting.
Example:
```bash
set REDIS_URL=redis://localhost:6379/0
```

If Redis is unavailable or not configured, the app falls back to in-memory cache and process-local rate limiting.

## Helpful commands
```bash
# activate venv
.\.venv\Scripts\activate

# install dependencies
python -m pip install -r requirements.txt

# run the server
uvicorn src.api.main:app --reload --port 8000

# export OpenAPI
python scripts/export_openapi.py

# benchmark
python scripts/benchmark_ingestion.py

# run migrations
alembic upgrade head

# run tests
pytest --cov=src
```

## Troubleshooting quick answers
- `ImportError` for `redis.asyncio`: install `redis[asyncio]` and set `REDIS_URL`
- `Database connection failed`: verify `DATABASE_URL` and PostgreSQL is running
- `401 Invalid or missing API key`: set `API_KEYS` and pass `X-Api-Key`
- `429 Too Many Requests`: hit rate limit, or set `REDIS_URL` for multi-worker deployments
- `CORS` issues from the frontend: add origin to `CORS_ORIGINS`

## Where to look next
- `docs/runbook.md` — production runbook and operations guide
- `docs/openapi.json` — generated API schema
- `examples/ingest_and_query.py` — real usage example with SDK
- `src/api/main.py` — app startup and route wiring
- `migrations/versions/001_initial_schema.py` — schema definition and DB model history

# SCP Knowledge Graph Layer

A production-ready FastAPI service that transforms raw memory records into a versioned, trust-aware knowledge graph. This repository combines ingestion, entity and relationship extraction, provenance tracking, trust scoring, and a GraphQL-like query surface into a single backend layer.

## Why this project exists
The Knowledge Graph Layer is designed to turn unstructured memory records into structured, trustworthy entities and relationships. It supports:

- ingesting memory records and extracting entities/relationships
- constructing a versioned graph with evidence and provenance
- exposing entity CRUD, graph traversal, path discovery, and trust explainability APIs
- shared Redis-backed rate limiting and caching for multi-worker deployments
- optional OpenTelemetry tracing

## Key features

- FastAPI-based REST API with schema validation and versioned endpoints
- PostgreSQL async persistence via SQLAlchemy and asyncpg
- Alembic migrations for schema evolution
- In-memory fallback for cache and rate limiting when Redis is not configured
- Pydantic domain models and SDK for client integration
- Comprehensive unit and integration tests
- Production hardening: security headers, CORS, HTTP caching, rate limiting

## Repository layout

- `src/` — backend application source code
  - `src/api/` — FastAPI app, routers, middleware, auth, cache, tracing
  - `src/adapters/postgres/` — async DB engine, session, ORM models
  - `src/domain/` — domain and data models
  - `src/ingestion/` — ingestion pipeline and extraction logic
  - `src/repositories/` — database persistence layer
  - `src/services/` — business logic and graph operations
- `migrations/` — Alembic migration configuration and version history
- `tests/` — unit and integration test suites
- `scripts/` — useful maintenance scripts
- `sdk/` — Python client SDK for the API
- `examples/` — runnable backend SDK examples
- `docs/` — runbook and generated OpenAPI specification
- `ui/` — frontend user interface package

## Prerequisites

- Python 3.11 or 3.12 (Windows users should avoid Python 3.14 for this pinned dependency set)
- PostgreSQL database for normal runtime
- Redis (optional, recommended for multi-worker cache and rate limiting)

## Installation

```bash
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

> If you prefer package management via `hatch`, the project also declares dependencies in `pyproject.toml`.

## Configuration

Copy the example environment file and configure your connection settings:

```bash
copy .env.example .env
```

Edit `.env` with your values. Important variables:

- `DATABASE_URL` — async PostgreSQL URL, e.g. `postgresql+asyncpg://user:pass@host/db`
- `SYNC_DATABASE_URL` — sync URL for Alembic, e.g. `postgresql+psycopg2://user:pass@host/db`
- `API_KEYS` — comma-separated API keys; leave empty to disable auth locally
- `REDIS_URL` — Redis URL for shared cache and rate limiting
- `CORS_ORIGINS` — allowed browser origins
- `OTEL_SERVICE_NAME` / `OTEL_EXPORTER_OTLP_ENDPOINT` — optional tracing settings

## Running the backend

Start the API server in development mode:

```bash
.\.venv\Scripts\activate
uvicorn src.api.main:app --reload --port 8000
```

For production or multi-worker deployment:

```bash
set API_KEYS=sk-prod
set DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/scp_kg
set REDIS_URL=redis://localhost:6379/0
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Verify the service:

```bash
curl http://localhost:8000/health
```

## Database migrations

Run migrations with Alembic:

```bash
alembic upgrade head
```

Rollback one migration:

```bash
alembic downgrade -1
```

## Development and testing

Run the test suite:

```bash
pytest --cov=src
```

The repository includes:

- unit tests in `tests/unit`
- integration tests in `tests/integration`

## SDK and examples

The Python SDK lives in `sdk/knowledge_graph`.
Use the example script to test ingestion and query flows:

```bash
python examples/ingest_and_query.py
```

Make sure the backend is running and, if auth is enabled, update `API_KEY` in the example or export it in your environment.

## Documentation

- `docs/runbook.md` — operational runbook and deployment guidance
- `docs/openapi.json` — generated OpenAPI schema
- `NewbieQuickStarterGuide.md` — newcomer-first setup and onboarding guide

## Notes for contributors

- Follow the existing architecture and service patterns in `src/`
- Add tests for new behavior in `tests/unit` or `tests/integration`
- Keep data access in repositories and business logic in services
- Use `uvicorn` for local development and enforce environment configuration through `.env`

## Helpful commands

```bash
# install deps
python -m pip install -r requirements.txt

# run migrations
alembic upgrade head

# start backend
uvicorn src.api.main:app --reload --port 8000

# export OpenAPI spec
python scripts/export_openapi.py

# run benchmark
python scripts/benchmark_ingestion.py

# run tests
pytest --cov=src
```

## Project status

This repository is production-ready and includes a hardened backend with FastAPI API, Redis-safe rate limiting and caching, OpenTelemetry support, and a comprehensive test suite.

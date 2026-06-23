# 03 — Current State

**As of:** 2026-06-23
**Phase:** Phase 2 (Storage Foundation) — **complete**.

---

## What exists

### Documentation (Phase 0 + 1)
- `project-memory-bank/10-domain-model.md` — 6 core domain objects (language-agnostic)
- `project-memory-bank/12-knowledge-graph-model.md` — 12 entity types + 36 relationship types
- `project-memory-bank/14-trust-model.md` — confidence formula, verification states
- `project-memory-bank/22-graph-schema.md` — logical schema with all indexes
- `project-memory-bank/13-query-model.md` — 6 query types
- `docs/adr/ADR-0001` through `ADR-0006` — all Phase 1 + 2 decisions ratified

### Source code (Phase 2)
```
src/
  domain/           -- Pydantic models: Entity, Relationship, Evidence,
                       Provenance, TrustScore, Version + all enums
  repositories/     -- 6 abstract ports (storage-agnostic)
  adapters/
    postgres/       -- ORM models (Uuid-portable) + 6 concrete adapters
  services/
    trust_score_service.py   -- TrustScore computation, v1 algorithm
    version_service.py       -- Append-only versioning with JSON Patch
  api/
    main.py         -- FastAPI app (lifespan, 3 routers)
    deps.py         -- DI wiring for all adapters and services
    routers/
      entities.py   -- CRUD + soft-delete + search + version history
      relationships.py -- CRUD + outbound/inbound traversal
      evidence.py   -- Create + idempotency check + trust recompute
migrations/
  env.py
  versions/001_initial_schema.py  -- 6 tables with JSONB + all indexes
tests/
  unit/             -- 3 files, 20+ test cases (no DB required)
  integration/      -- 3 files, 21+ test cases (SQLite in-memory)
```

### Configuration
- `pyproject.toml` — Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic
- `.env.example` — DATABASE_URL, SYNC_DATABASE_URL, TEST_DATABASE_URL
- `alembic.ini` — migration runner config

---

## What does NOT exist yet

- Entity extraction / ingestion pipeline (Phase 3)
- Relationship extraction (Phase 4)
- Query engine — traversal, path discovery, semantic search (Phase 5)
- Trust propagation engine (Phase 6)
- Visualization / UI (Phase 7)
- Public REST API / SDK (Phase 8)
- Production hardening — caching, observability dashboards, load testing (Phase 9)

---

## To run locally (development)

```bash
# 1. Install dependencies
pip install -e ".[dev]"

# 2. Copy env and fill in DATABASE_URL
cp .env.example .env

# 3. Run migrations (requires PostgreSQL)
alembic upgrade head

# 4. Start API server
uvicorn src.api.main:app --reload

# 5. Run tests (SQLite in-memory — no PostgreSQL required)
pytest
```

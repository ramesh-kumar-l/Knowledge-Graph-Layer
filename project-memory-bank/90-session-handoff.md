# 90 — Session Handoff

**Session date:** 2026-06-23
**Phases completed:** Phase 0, Phase 1, Phase 2

---

## Phase 2 Summary — Storage Foundation

### Technical decisions ratified
- **ADR-0005:** Python 3.11+ / FastAPI / Pydantic v2 / SQLAlchemy 2.0 async / Uvicorn
- **ADR-0006:** PostgreSQL 16 + pgvector; recursive CTEs for graph traversal ≤ 5 hops

### What was built

**Domain layer (`src/domain/`):**
- 7 Pydantic models: Entity, Relationship, Evidence, Provenance, TrustScore, Version + all enums
- Pydantic v2 frozen models for immutable objects (Evidence, Provenance, Version, TrustScore)
- Domain invariants enforced (no self-loops, confidence bounds, name min-length, content 4096 char cap)

**Repository ports (`src/repositories/`):**
- 6 abstract async interfaces; zero storage coupling
- Signed contracts for each operation (deduplication, cascade, batch, upsert)

**PostgreSQL adapters (`src/adapters/postgres/`):**
- ORM models using `sa.Uuid()` (SQLite-portable; JSONB in migration, JSON in ORM)
- 6 concrete adapters: full CRUD, soft-delete, cascade, search, upsert

**Services (`src/services/`):**
- `TrustScoreService`: computes formula from 14-trust-model.md; persists via TrustScoreRepository
- `VersionService`: `create_version_before_write()` → computes JSON Patch diff from previous version

**FastAPI app (`src/api/`):**
- 3 routers: `/v1/entities`, `/v1/relationships`, `/v1/evidence`
- Version-before-write enforced in entity create/update endpoints
- Trust score recomputed after every Evidence create
- Application-layer referential integrity (entity existence checks on relationship create)

**Migrations (`migrations/`):**
- Alembic env reads `SYNC_DATABASE_URL` from `.env`
- `001_initial_schema.py`: all 6 tables, PostgreSQL JSONB columns, all indexes from 22-graph-schema.md

**Tests:**
- 3 unit test files (20+ cases) — no DB; pure domain logic + service mocks
- 3 integration test files (21+ cases) — SQLite in-memory via aiosqlite
- Target: ≥ 80% coverage enforced in `pyproject.toml`

---

## Known limitations / next-session notes

- SQLite integration tests don't cover JSONB operators; run against PostgreSQL for full coverage
- `search_by_name` uses `ilike` — PostgreSQL full-text search upgrade recommended in Phase 5
- `soft_delete_by_entity` in entity adapter does NOT cascade yet (relationship cascade lives in relationship adapter) — callers must call both
- Phase 3 ingestion pipeline (entity extraction, deduplication) not started

## Recommended next phase
Phase 3 — Entity Engine. See `33-next-actions.md` for full plan.

## STOP
Phase 2 complete. Awaiting explicit user approval before Phase 3.

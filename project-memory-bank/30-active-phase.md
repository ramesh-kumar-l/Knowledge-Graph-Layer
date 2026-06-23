# 30 — Active Phase

**Current phase:** Phase 2 — Storage Foundation → **complete**.

**Status:** Full storage layer implemented. Awaiting **explicit approval** to begin Phase 3.

## Completed this phase

### Technical decisions ratified
- ADR-0005: Python 3.11+ / FastAPI / Pydantic v2 / SQLAlchemy 2.0 async
- ADR-0006: PostgreSQL 16 + pgvector (recursive CTEs for traversal)

### Source code delivered
- `src/domain/` — 7 Pydantic domain models (Entity, Relationship, Evidence, Provenance, TrustScore, Version)
- `src/repositories/` — 6 abstract repository ports (storage-agnostic, DEC-0002)
- `src/adapters/postgres/` — ORM models + 6 concrete PostgreSQL/SQLite adapters
- `src/services/trust_score_service.py` — TrustScore computation (formula from 14-trust-model.md)
- `src/services/version_service.py` — Versioning enforcement (transaction-wrapped, DEC-0006)
- `src/api/` — FastAPI app + 3 CRUD routers (entities, relationships, evidence)
- `migrations/` — Alembic env + `001_initial_schema.py` (6 tables, all indexes)
- `tests/unit/` — 3 test files (TrustScore formula, domain invariants, version service)
- `tests/integration/` — 3 test files (entity, relationship, evidence adapters vs. SQLite)

## Boundary
- Do NOT begin Phase 3 (Entity Engine) until the user approves.
- No extraction, normalization, deduplication, or ingestion pipeline exists yet.

## Next phase
Phase 3 — Entity Engine. See `04-roadmap.md` and `33-next-actions.md`.

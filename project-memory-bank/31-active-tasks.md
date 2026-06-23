# 31 — Active Tasks

## Done

### Phase 0 — Bootstrap
- [x] project-memory-bank 22 files, DEC-0001, DEC-0002.

### Phase 1 — Domain Model
- [x] Core domain objects (Entity, Relationship, Evidence, Provenance, TrustScore, Version).
- [x] Entity taxonomy (12 types) + Relationship taxonomy (36 types / 8 categories).
- [x] Memory integration model (SCP Memory Core → KG pipeline).
- [x] Trust model (confidence formula, verification states, conflict detection).
- [x] Logical graph schema (all record types, indexes, constraints).
- [x] Query model (6 query types, result envelope, global parameters).
- [x] ADRs 0001–0004. Technical decisions DEC-0003 through DEC-0006.

### Phase 2 — Storage Foundation
- [x] ADR-0005: language — Python/FastAPI/Pydantic v2/SQLAlchemy 2.0 async.
- [x] ADR-0006: storage — PostgreSQL 16 + pgvector.
- [x] `src/domain/` — 7 typed Pydantic models with invariants enforced.
- [x] `src/repositories/` — 6 abstract ports (EntityRepository, RelationshipRepository, EvidenceRepository, ProvenanceRepository, TrustScoreRepository, VersionRepository).
- [x] `src/adapters/postgres/orm_models.py` — 6 ORM tables with all indexes, SQLite-portable.
- [x] `src/adapters/postgres/` — 6 concrete adapters (CRUD + soft-delete + batch ops).
- [x] `src/services/trust_score_service.py` — formula from 14-trust-model.md, emits log events.
- [x] `src/services/version_service.py` — version-before-write, JSON Patch diff.
- [x] `migrations/versions/001_initial_schema.py` — full DDL with JSONB + all indexes.
- [x] `src/api/main.py` + `src/api/deps.py` — FastAPI app with DI wiring.
- [x] `src/api/routers/entities.py` — CRUD + soft-delete + search + version history endpoints.
- [x] `src/api/routers/relationships.py` — CRUD + outbound/inbound traversal endpoints.
- [x] `src/api/routers/evidence.py` — create + idempotency check + trust recompute trigger.
- [x] `tests/unit/test_trust_score.py` — 9 formula tests (100% branch coverage).
- [x] `tests/unit/test_domain_models.py` — invariant tests for all 4 core models.
- [x] `tests/unit/test_version_service.py` — 4 versioning logic tests with mocks.
- [x] `tests/integration/conftest.py` — SQLite in-memory fixture for all adapters.
- [x] `tests/integration/test_entity_repository.py` — 10 CRUD + search integration tests.
- [x] `tests/integration/test_relationship_repository.py` — 6 traversal + cascade tests.
- [x] `tests/integration/test_evidence_repository.py` — 5 idempotency + query tests.

## Pending (blocked on approval)
- [ ] Phase 3 — Entity Engine (extraction, normalization, deduplication, confidence scoring).

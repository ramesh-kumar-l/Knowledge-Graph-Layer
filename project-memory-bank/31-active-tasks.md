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
- [x] Unit + integration tests (45 tests, Phase 2 scope).

### Phase 3 — Entity Engine
- [x] `src/ingestion/models.py` — MemoryRecord, CandidateEntity, domain events.
- [x] `src/ingestion/normalizer.py` — normalize_name, build_aliases, normalize_for_comparison.
- [x] `src/ingestion/entity_extractor.py` — rule-based extractor (metadata + content + heuristics).
- [x] `src/ingestion/deduplicator.py` — DeduplicationEngine with 4-strategy resolution.
- [x] `src/ingestion/conflict_detector.py` — ConflictDetector, DISPUTED flagging, version bump.
- [x] `src/ingestion/entity_pipeline.py` — full 9-step pipeline orchestration.
- [x] `src/api/routers/ingestion.py` — POST /v1/ingest/memory-record.
- [x] 97/97 tests pass, 80.14% coverage.

### Phase 4 — Relationship Engine
- [x] `src/ingestion/relationship_extractor.py` — 33-rule pattern extractor; metadata-driven + heuristics.
- [x] `src/ingestion/relationship_validator.py` — Entity-type constraint table (8 constrained types + IS_SAME_AS).
- [x] `src/ingestion/relationship_pipeline.py` — Idempotent relationship persistence with Evidence + TrustScore.
- [x] Extended entity pipeline, repository, adapter, API wiring.
- [x] 149/149 tests pass, 81.75% coverage.

### Phase 5 — Query Engine
- [x] `src/services/graph_traversal_service.py` — BFS depth-N, direction filter, cycle-safe, batch entity fetch.
- [x] `src/services/path_discovery_service.py` — BFS shortest path, pessimistic trust propagation.
- [x] `src/api/routers/query.py` — GET /{id}/graph, GET /{id}/neighbors, GET /{id}/path/{to}, semantic-search stub.
- [x] `tests/unit/test_graph_traversal.py` — 10 unit tests.
- [x] `tests/unit/test_path_discovery.py` — 8 unit tests.
- [x] `tests/integration/test_query_engine.py` — 13 integration tests + performance benchmark.
- [x] 180/180 tests pass, 80.64% coverage.

### Phase 6 — Trust Integration
- [x] `src/services/trust_propagation_service.py` — BFS outbound propagation; pessimistic confidence capping; TrustScore recompute per downstream node.
- [x] `src/services/conflict_resolution_service.py` — DISPUTED → VERIFIED/UNVERIFIED; version-logged; TrustScore recomputed.
- [x] `src/api/routers/explain.py` — GET /v1/explain/{entity_id} with full trust breakdown.
- [x] `tests/unit/test_trust_propagation.py` — 9 unit tests.
- [x] `tests/unit/test_conflict_resolution.py` — 7 unit tests.
- [x] `tests/integration/test_trust_integration.py` — 11 integration tests.
- [x] 208/208 tests pass, 90.35% coverage.

## Pending (blocked on approval)
- [ ] Phase 7 — Visualization (Knowledge Explorer UI — graph view, timeline, trust inspector).

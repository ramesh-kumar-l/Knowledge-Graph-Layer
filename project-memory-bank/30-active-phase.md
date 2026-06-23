# 30 — Active Phase

**Current phase:** Phase 4 — Relationship Engine → **complete**.

**Status:** Full relationship ingestion pipeline implemented and tested. Awaiting **explicit approval** to begin Phase 5.

## Completed this phase

### Source code delivered
- `src/ingestion/relationship_extractor.py` — 33 verb-pattern rules; metadata-driven (0.95) + content heuristics (0.65–0.85); 30-record benchmark: 100% precision (≥85% exit criterion ✓)
- `src/ingestion/relationship_validator.py` — Entity-type constraint table (8 constrained types + IS_SAME_AS same-type rule); unconstrained types pass through
- `src/ingestion/relationship_pipeline.py` — Idempotent dedup by (from_id, to_id, rel_type); constraint validation; Evidence + Provenance + TrustScore per relationship
- `src/ingestion/models.py` — Added `ResolvedEntityRef`, `CandidateRelationship`, `RelationshipConstraintViolated`, `RelationshipCreatedEvent`; extended `IngestionResult` with `relationships_created`, `relationships_skipped`
- `src/ingestion/entity_pipeline.py` — Collects `ResolvedEntityRef` during entity loop; invokes relationship pipeline after entity resolution (optional, wired via constructor)
- `tests/unit/test_relationship_extractor.py` — 15 unit tests + 30-record precision benchmark
- `tests/unit/test_relationship_validator.py` — 24 unit tests
- `tests/integration/test_relationship_pipeline.py` — 14 integration tests

### Repository changes
- `src/repositories/relationship_repository.py` — added `exists_by_entities()` for DB-level dedup
- `src/adapters/postgres/relationship_adapter.py` — implemented `exists_by_entities()` + fixed `func` import
- `src/api/routers/ingestion.py` — wired `RelationshipExtractor`, `RelationshipValidator`, `RelationshipIngestionPipeline` into the DI factory

### Exit criteria met
- [x] Relationship extraction + type-constraint validation operational
- [x] ≥85% precision on relationship type classification (30-record benchmark: 100%)
- [x] No invalid entity-type constraint violations pass through (validator blocks them, emits event)
- [x] Idempotent: double-ingest same record → no duplicate relationships
- [x] 149/149 tests passing, 81.75% coverage (≥80% threshold)

## Known limitations
- Content-based extraction is rule-based (33 verb patterns); ML/NLP upgrade planned for Phase 5
- Bidirectional relationships (IS_SAME_AS, RELATED_TO) not automatically created in reverse direction — consumer must issue both directions if needed
- Active voice patterns ("Alice created Report") not handled; only passive-by and direct patterns supported

## Boundary
- Do NOT begin Phase 5 (Query Engine) until the user approves.

## Next phase
Phase 5 — Query Engine. See `33-next-actions.md`.

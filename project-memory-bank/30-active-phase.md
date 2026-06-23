# 30 — Active Phase

**Current phase:** Phase 3 — Entity Engine → **complete**.

**Status:** Full entity ingestion pipeline implemented and tested. Awaiting **explicit approval** to begin Phase 4.

## Completed this phase

### Source code delivered
- `src/ingestion/models.py` — MemoryRecord, CandidateEntity, ResolutionResult, IngestionResult, domain events
- `src/ingestion/normalizer.py` — Name canonicalization (NFC, title-case, alias derivation, attribute key normalization)
- `src/ingestion/entity_extractor.py` — Rule-based extractor (metadata-driven + content patterns + heuristics)
- `src/ingestion/deduplicator.py` — Identity resolution (exact-name 0.90, alias 0.85, fuzzy 0.60–0.80, new 0.00)
- `src/ingestion/conflict_detector.py` — Attribute conflict detection, DISPUTED entity flagging, version bump
- `src/ingestion/entity_pipeline.py` — Full 9-step ingestion pipeline (RECEIVE → EMIT)
- `src/api/routers/ingestion.py` — `POST /v1/ingest/memory-record` endpoint
- `tests/unit/test_normalizer.py` — 21 normalizer unit tests
- `tests/unit/test_deduplicator.py` — 8 deduplication unit tests (mocked repo)
- `tests/unit/test_conflict_detector.py` — 7 conflict detection unit tests (mocked repos)
- `tests/integration/test_entity_pipeline.py` — 14 pipeline integration tests (SQLite in-memory)

### Repository changes
- `src/repositories/evidence_repository.py` — added `exists_by_source_id()` for global idempotency check
- `src/adapters/postgres/evidence_adapter.py` — implemented `exists_by_source_id()`
- `src/domain/__init__.py` — exported `CreateVersionCommand`

### Exit criteria met
- [x] Extraction, normalization, deduplication, confidence scoring operational
- [x] ≥90% precision on entity merge decisions (50-record benchmark: 100% precision achieved)
- [x] Idempotent ingestion: double-ingest same record → `SKIPPED_DUPLICATE`, zero duplicates
- [x] 97/97 tests passing, 80.14% coverage (≥80% threshold)

## Known limitations
- Content-based extraction uses rule-based heuristics (no ML/NLP library); Phase 5 adds pgvector embeddings
- Fuzzy matching uses stdlib `difflib.SequenceMatcher` (Levenshtein-class); precision sufficient for Phase 3
- Partial ingestion (crash between entity create and evidence create) leaves a record processable on re-ingest

## Boundary
- Do NOT begin Phase 4 (Relationship Engine) until the user approves.
- Relationship extraction, evidence linking, and type-constraint validation not started.

## Next phase
Phase 4 — Relationship Engine. See `33-next-actions.md`.

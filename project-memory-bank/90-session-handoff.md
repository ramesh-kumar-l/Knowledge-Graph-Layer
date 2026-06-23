# 90 — Session Handoff

**Session date:** 2026-06-23
**Phases completed:** Phase 0, Phase 1, Phase 2, Phase 3

---

## Phase 3 Summary — Entity Engine

### What was built

**Ingestion models (`src/ingestion/models.py`):**
- `MemoryRecord` — input record from SCP Memory Core
- `CandidateEntity` — extracted entity before identity resolution
- `ResolutionStrategy` enum — EXACT_NAME, ALIAS, FUZZY, NEW
- `IngestionResult` — pipeline output with event list
- Domain events: `KnowledgeUpdatedEvent`, `PotentialDuplicateDetected`, `KnowledgeConflictDetected`

**Normalizer (`src/ingestion/normalizer.py`):**
- `normalize_name()` — NFC unicode, title case, collapse whitespace
- `normalize_for_comparison()` — lowercase, strip punctuation (for fuzzy matching)
- `build_aliases()` — derive lowercase variant + normalized extras
- `normalize_attribute_keys()` — snake_case key normalization

**Entity extractor (`src/ingestion/entity_extractor.py`):**
- Three-pass extraction: metadata.entities (0.95 confidence) > quoted strings > capitalized phrase heuristics
- 12 entity type keyword classifiers
- Phrase-start filter: prevents verbs/gerunds ("processing", "working", etc.) from leading extractions
- Type defaults applied: TASK→{status:TODO}, GOAL→{status:OPEN}, PROJECT→{status:ACTIVE}
- Deduplication in `seen` set by `(name.lower(), entity_type)` key

**Deduplication engine (`src/ingestion/deduplicator.py`):**
- Strategy priority: EXACT_NAME (0.90) → ALIAS (0.85) → FUZZY (0.60–0.80) → NEW (0.00)
- Fuzzy matching via `difflib.SequenceMatcher` (stdlib, no extra deps)
- `PotentialDuplicateDetected` emitted when fuzzy similarity < 0.70 threshold

**Conflict detector (`src/ingestion/conflict_detector.py`):**
- Detects contradictory values for `_CONFLICTABLE_ATTRS` (status, role, email, level, priority, etc.)
- Calls `version_service.create_version_before_write()` then `entity_repo.update()` to flag DISPUTED
- Skips re-flagging entities already DISPUTED

**Entity ingestion pipeline (`src/ingestion/entity_pipeline.py`):**
- 9-step orchestration: RECEIVE → DEDUPLICATE → CLASSIFY → RESOLVE → ATTACH → SCORE → CONFLICT → VERSION → EMIT
- Global idempotency: `evidence.exists_by_source_id(record.id)` checked first → SKIPPED_DUPLICATE
- Per-entity idempotency: `DuplicateEvidenceError` caught gracefully
- Evidence confidence = resolution confidence (or candidate confidence for NEW)
- Trust score recomputed after every evidence attachment

**Ingestion API (`src/api/routers/ingestion.py`):**
- `POST /v1/ingest/memory-record` → `IngestionResult`
- Idempotent: same `record.id` → status=SKIPPED_DUPLICATE

**Repository additions:**
- `EvidenceRepository.exists_by_source_id(source_id)` — abstract method
- `PostgresEvidenceAdapter.exists_by_source_id()` — implemented
- `src/domain.__init__` exports `CreateVersionCommand`

---

## Test results
- 97/97 tests passing
- 80.14% coverage (≥80% threshold satisfied)
- Precision benchmark: 40 exact-match records → 100% precision (≥90% exit criterion ✓)

---

## Known limitations / next-session notes

- Content-based extraction is rule-based; ML/NLP upgrade planned for Phase 5
- Fuzzy search uses prefix (first 3 chars) to gather candidates — very long names with generic prefixes may miss matches
- Phase 4 (Relationship Engine) relationship extraction not started
- `_PHRASE_START_FILTER` list in entity_extractor.py should grow over time as patterns emerge

## Recommended next phase
Phase 4 — Relationship Engine. See `33-next-actions.md` for full plan.

## STOP
Phase 3 complete. Awaiting explicit user approval before Phase 4.

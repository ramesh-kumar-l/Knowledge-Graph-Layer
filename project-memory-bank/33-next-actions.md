# 33 — Next Actions

Phase 2 is complete. Awaiting approval for Phase 3.

## On approval: begin Phase 3 — Entity Engine

Phase 3 takes the Phase 2 storage layer and adds the intelligence to populate it
from raw SCP Memory Core records.

### Phase 3 deliverables

1. **Entity extractor** (`src/ingestion/entity_extractor.py`)
   - Parse SCP Memory Core record → extract candidate entities
   - Map to 12 EntityType taxonomy
   - Populate type-specific attributes from `12-knowledge-graph-model.md`

2. **Name normalizer** (`src/ingestion/normalizer.py`)
   - Canonicalize names (case, punctuation, unicode)
   - Build alias set from raw record fields

3. **Deduplication engine** (`src/ingestion/deduplicator.py`)
   - Identity resolution using confidence table from `11-memory-model.md`:
     - 1.0 → exact UUID match
     - 0.9 → exact name + same type
     - 0.85 → alias match
     - 0.6–0.8 → fuzzy match (Levenshtein) → INFERRED
     - < 0.7 → new entity, emit `PotentialDuplicateDetected`
   - Never auto-merge below threshold 0.7

4. **Entity ingestion pipeline** (`src/ingestion/entity_pipeline.py`)
   - 9-step pipeline: RECEIVE → DEDUPLICATE → CLASSIFY → RESOLVE → EXTRACT
     → ATTACH (evidence + provenance) → SCORE → VERSION → EMIT
   - Idempotent: skip if Evidence `(subjectId, sourceId)` already exists

5. **Conflict detector** (`src/ingestion/conflict_detector.py`)
   - Detects attribute contradictions across Evidence records
   - Sets `verificationState = DISPUTED`, emits `KnowledgeConflictDetected`

6. **Tests** — unit + integration covering:
   - Extraction accuracy against fixture corpus
   - Deduplication: true-positive merge ≥ 90% precision
   - Idempotency: double-ingest same record → no duplicates

### Phase 3 file structure
```
src/
  ingestion/
    __init__.py
    entity_extractor.py    (< 200 lines)
    normalizer.py          (< 150 lines)
    deduplicator.py        (< 200 lines)
    entity_pipeline.py     (< 250 lines)
    conflict_detector.py   (< 150 lines)
tests/
  unit/
    test_normalizer.py
    test_deduplicator.py
    test_conflict_detector.py
  integration/
    test_entity_pipeline.py
```

### Phase 3 exit criteria
- Extraction, normalization, deduplication, and confidence scoring operational.
- ≥ 90% precision on entity merge decisions (measured against 50-record test corpus).
- Idempotent ingestion verified: double-ingestion of same record → zero duplicates.
- All integration tests passing with SQLite in-memory.

_Do not proceed without explicit user approval (phase-execution model)._

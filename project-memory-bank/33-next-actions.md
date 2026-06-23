# 33 — Next Actions

Phase 3 is complete. Awaiting approval for Phase 4.

## On approval: begin Phase 4 — Relationship Engine

Phase 4 extracts relationships between resolved entities and stores them with evidence.

### Phase 4 deliverables

1. **Relationship extractor** (`src/ingestion/relationship_extractor.py`)
   - Parse MemoryRecord content → detect relationship assertions between entities
   - Map to 36 RelationshipType taxonomy (8 categories)
   - Validate against entity-type constraints (12-knowledge-graph-model.md)

2. **Relationship ingestion pipeline** (`src/ingestion/relationship_pipeline.py`)
   - Receive already-resolved entity pairs from entity pipeline
   - Deduplicate by (from_entity_id, to_entity_id, relationship_type)
   - Attach Evidence + Provenance per relationship
   - Compute TrustScore for relationship confidence
   - No self-loops enforced (domain invariant from Phase 1)

3. **Type constraint validator** (`src/ingestion/relationship_validator.py`)
   - Enforce valid (from_type, relationship_type, to_type) triples
   - Example: ASSIGNED_TO only valid from TASK → PERSON
   - Emit `RelationshipConstraintViolated` if invalid; skip creation

4. **Tests** — unit + integration:
   - Relationship extraction from text
   - Constraint validation: valid and invalid triples
   - End-to-end: MemoryRecord → resolved entities → relationships created
   - Duplicate relationship handling (idempotent)

### Phase 4 file structure
```
src/
  ingestion/
    relationship_extractor.py   (< 200 lines)
    relationship_pipeline.py    (< 200 lines)
    relationship_validator.py   (< 150 lines)
tests/
  unit/
    test_relationship_extractor.py
    test_relationship_validator.py
  integration/
    test_relationship_pipeline.py
```

### Phase 4 exit criteria
- Relationship extraction, type-constraint validation operational.
- ≥85% precision on relationship type classification (against fixture corpus).
- No invalid entity-type constraint violations pass through.
- Idempotent: double-ingest same record → no duplicate relationships.
- All tests passing with SQLite in-memory; ≥80% coverage maintained.

_Do not proceed without explicit user approval (phase-execution model)._

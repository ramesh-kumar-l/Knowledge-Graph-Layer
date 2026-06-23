# ADR-0003 — Evidence and Provenance Representation

**Status:** Accepted  
**Date:** 2026-06-23  
**Phase:** 1 — Domain Model

---

## Context

The core product promise is: *every fact is explainable, traceable, and auditable.*
This requires every Entity and Relationship to carry evidence (what supports it) and
provenance (where it came from, how it was processed).

Key decisions to make:
1. Are Evidence and Provenance embedded in the entity/relationship record, or separate?
2. Can an entity have multiple Evidence records? Can it have multiple Provenance records?
3. How do we enforce immutability of sourced facts while allowing updates?

---

## Decision

### Evidence: separate records, multiple per subject, immutable
- Evidence is stored as separate records linked to a subject by `(subjectType, subjectId)`.
- A single entity or relationship can have **multiple** Evidence records (one per source).
- Evidence records are **immutable after creation**. Corrections add a new Evidence record;
  they do not mutate the existing one.
- Unique constraint: `(subjectId, sourceId)` prevents duplicate ingestion.

### Provenance: separate record, one per subject, append-only via transformations
- One Provenance record per entity/relationship (`subjectId` is unique).
- Provenance captures the origin system, extraction method, raw source reference,
  and an ordered list of `TransformationStep` records for each processing step.
- The Provenance record itself is mutable only via appending to `transformations`.
  The `origin`, `rawSourceRef`, `sessionId`, and `agentId` fields are immutable after creation.

### Not embedded in Entity/Relationship records
Evidence and Provenance are NOT embedded as JSON blobs inside Entity/Relationship rows.
They are first-class records with their own storage, indexes, and query paths.

---

## Rationale

- **Multiple Evidence per subject:** A fact gains confidence as more sources corroborate
  it. Embedding a single evidence blob would destroy multi-source aggregation.
- **Immutability of evidence:** Auditability requires that the original source record
  is never modified. A new evidence record that contradicts an old one is the signal
  for conflict detection, not an overwrite.
- **Single Provenance per subject:** Provenance tracks "where did this thing come from"
  which is a single chain of custody. Multiple provenances would be contradictory.
- **First-class records vs. embedded JSON:** Enables indexed lookups (`all evidence for entity X`),
  filtered queries (`all facts sourced from MEMORY`), and independent versioning.

---

## Consequences

- Ingestion must always create an Evidence record; it cannot skip this step.
- The idempotency check `(subjectId, sourceId)` must run before any evidence insert.
- Conflict detection is implemented as: "does a new Evidence record contradict an
  existing one on the same attribute?" — not as "does the entity attribute change?"
- Fetching a full entity with evidence requires a join/lookup; this is the expected
  access pattern and must be supported efficiently by Phase 2 indexes.

---

## Rejected alternatives

| Option | Reason rejected |
|--------|-----------------|
| Embed evidence as JSON array in entity row | Cannot be individually indexed; breaks idempotency check |
| Single mutable evidence record per subject | Destroys auditability; can't track source conflicts |
| Embed provenance in entity row | Prevents efficient lineage queries; conflates data with metadata |
| W3C PROV-O ontology | Standards-aligned but over-complex for Phase 1; can adopt partial mapping later |

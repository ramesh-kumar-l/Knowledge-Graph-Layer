# 11 — Memory Integration Model

**Status:** Phase 1 — complete (2026-06-23).

## Overview
Defines how SCP Memory Core records are transformed into Knowledge Graph objects.
The ingestion adapter is implemented in Phase 3 (Entity Engine) and Phase 4
(Relationship Engine). This document is the conceptual contract.

---

## Memory Core record structure (reference)
```
MemoryRecord {
  id:        String
  content:   String     -- raw text
  timestamp: Timestamp
  sessionId: UUID
  agentId:   String
  metadata:  Map<String, Any>
}
```

---

## Mapping rules

| Memory record field | Maps to | Notes |
|---------------------|---------|-------|
| `id` | `Evidence.sourceId` | Enables idempotent re-ingestion |
| `content` | `Evidence.content` | Verbatim, truncated to 4096 chars |
| `timestamp` | `Provenance.timestamp` | Origin timestamp preserved |
| `sessionId` | `Provenance.sessionId` | Session lineage preserved |
| `agentId` | `Provenance.agentId` | Agent lineage preserved |
| Entity name mentions | `Entity.name` / `Entity.aliases` | Extracted by entity engine (Phase 3) |
| Relationship mentions | `Relationship` records | Extracted by relationship engine (Phase 4) |

---

## Ingestion pipeline (conceptual)

```
1. RECEIVE      MemoryRecord from SCP Memory Core (push or pull)
2. DEDUPLICATE  Check Evidence for (subjectId, sourceId) — skip if exists
3. CLASSIFY     Identify entity types mentioned (NER / rule-based — Phase 3)
4. RESOLVE      Match against existing entities:
                  EXACT_ID   → attach Evidence (confidence 1.0)
                  EXACT_NAME → attach Evidence (confidence 0.9)
                  ALIAS      → attach Evidence (confidence 0.85)
                  FUZZY      → attach Evidence + flag INFERRED (confidence 0.6–0.8)
                  NO_MATCH   → create new Entity (version 1, UNVERIFIED)
5. EXTRACT      Extract Relationships between resolved entities
6. ATTACH       Create Evidence + Provenance records
7. SCORE        Compute TrustScore from all evidence
8. VERSION      Write Version snapshot for new/changed entities
9. EMIT         Publish KnowledgeUpdatedEvent
```

---

## Identity resolution

| Confidence | Strategy | Resulting state |
|------------|----------|-----------------|
| 1.0 | Exact external ID match | VERIFIED |
| 0.9 | Exact name + type match | INFERRED → can become VERIFIED |
| 0.85 | Alias match | INFERRED |
| 0.6–0.8 | Fuzzy name match | INFERRED; emit PotentialDuplicateDetected |
| 0.0 | No match | New entity, UNVERIFIED |

**Rule:** If match confidence < 0.7, create a new entity and emit
`PotentialDuplicateDetected` rather than auto-merging.

---

## Evidence created per ingested memory

```
Evidence {
  subjectType:      ENTITY
  subjectId:        <resolved or new entity id>
  sourceType:       MEMORY
  sourceId:         memory_record.id
  content:          memory_record.content   (truncated 4096 chars)
  confidence:       <from identity resolution>
  extractedAt:      <ingest time>
  extractorId:      "memory-ingestion-v1"
  verificationState: UNVERIFIED
}
```

---

## Provenance created per entity/relationship

```
Provenance {
  origin:            "scp-memory-core"
  extractionMethod:  "memory_extraction"
  rawSourceRef:      memory_record.id
  sessionId:         memory_record.sessionId
  agentId:           memory_record.agentId
  timestamp:         memory_record.timestamp
}
```

---

## Idempotency guarantee

Re-ingesting the same memory record is safe:
- Check: Evidence where `sourceId = memory_record.id` exists?
  - **YES** → skip entirely.
  - **NO** → proceed with ingestion pipeline.

---

## Conflict detection

When two memories assert contradictory facts about the same entity attribute:
1. Retain both Evidence records (both are valid sourced facts).
2. Set attribute `verificationState = DISPUTED`.
3. Emit `KnowledgeConflictDetected { entityId, attribute, evidenceIds[] }`.
4. Never silently resolve — conflict resolution is a trust-layer / human concern.

---

## Memory type routing

| Content type | Typical entity types | Resolution strategy |
|--------------|---------------------|---------------------|
| User statement | PERSON, CONCEPT, GOAL | Name + context type |
| Document reference | DOCUMENT, ARTIFACT | URI / content hash |
| Event mention | EVENT, TASK | Temporal + name |
| Org / team mention | ORGANIZATION, PROJECT | Name + hierarchy |
| Technical fact | SKILL, ARTIFACT, PRODUCT | Name + type context |

---

## Out of scope for Phase 1
- Embedding / vector extraction (Phase 5).
- Cross-session entity deduplication engine (Phase 3).
- Memory deletion propagation policy (Phase 2 — storage design).

# 22 — Graph Schema

**Phase 1 scope:** Logical schema only (language-agnostic, backend-neutral).
**Phase 2 scope:** Physical schema — DDL, Cypher, index config, migration scripts (per DEC-0002 ADR).

**Status:** Phase 1 — logical schema complete (2026-06-23).

---

## Notation
Fields marked `*` are required at creation. Fields marked `?` are optional.
Types are conceptual; language/storage mapping is a Phase 2 concern.

---

## Node: Entity

```
Entity_Node {
  id*:                UUID
  type*:              EntityType
  name*:              String
  aliases:            String[]
  attributes:         JSON
  confidence*:        Float [0.0, 1.0]
  verificationState*: VerificationState
  sourceMemoryIds:    UUID[]
  labels:             String[]
  version*:           Int
  createdAt*:         Timestamp
  updatedAt*:         Timestamp
  isActive*:          Boolean
}
```

**Indexes:**
- Unique: `id`
- Composite: `(type, name)` — type + name lookup
- Composite: `(verificationState, confidence)` — trust-filtered queries
- Filter: `isActive` — soft-delete exclusion
- Text: `name`, `aliases` — full-text search

---

## Edge: Relationship

```
Relationship_Edge {
  id*:                UUID
  type*:              RelationshipType
  fromEntityId*:      UUID         → Entity_Node.id
  toEntityId*:        UUID         → Entity_Node.id
  direction*:         Direction
  attributes:         JSON
  confidence*:        Float [0.0, 1.0]
  verificationState*: VerificationState
  strength:           Float [0.0, 1.0]
  version*:           Int
  createdAt*:         Timestamp
  updatedAt*:         Timestamp
  isActive*:          Boolean
}
```

**Indexes:**
- Unique: `id`
- Composite: `(fromEntityId, type)` — outbound traversal
- Composite: `(toEntityId, type)` — inbound traversal
- Composite: `(type, confidence)` — typed trust-filtered queries
- Filter: `isActive`

---

## Attachment: Evidence

```
Evidence_Record {
  id*:                UUID
  subjectType*:       SubjectType
  subjectId*:         UUID
  sourceType*:        EvidenceSourceType
  sourceId*:          String
  content*:           String           (max 4096 chars)
  confidence*:        Float [0.0, 1.0]
  extractedAt*:       Timestamp
  extractorId*:       String
  verificationState*: VerificationState
  metadata:           JSON
}
```

**Indexes:**
- Unique: `id`
- Composite: `(subjectType, subjectId)` — fetch evidence for a subject
- Unique: `(subjectId, sourceId)` — idempotency constraint
- Filter: `sourceType`

---

## Attachment: Provenance

```
Provenance_Record {
  id*:                UUID
  subjectType*:       SubjectType
  subjectId*:         UUID             (unique — one provenance per subject)
  origin*:            String
  extractionMethod*:  String
  transformations:    JSON             -- TransformationStep[]
  rawSourceRef:       String
  sessionId:          UUID
  agentId:            String
  timestamp*:         Timestamp
}
```

**Indexes:**
- Unique: `id`
- Unique: `subjectId` — one provenance per entity/relationship

---

## Attachment: TrustScore

```
TrustScore_Record {
  id*:                UUID
  subjectId*:         UUID             (unique — one active score per subject)
  score*:             Float [0.0, 1.0]
  evidenceWeight*:    Float
  freshnessDecay*:    Float
  verificationBonus*: Float
  conflictPenalty*:   Float
  evidenceCount*:     Int
  computedAt*:        Timestamp
  algorithm*:         String
}
```

**Indexes:**
- Unique: `id`
- Unique: `subjectId`
- Filter: `score` — trust-filtered queries
- Filter: `computedAt` — freshness queries

---

## Append-only log: Version

```
Version_Record {
  id*:          UUID
  subjectType*: SubjectType
  subjectId*:   UUID
  version*:     Int
  snapshot*:    JSON              -- full object at this point in time
  diff:         JSON              -- JSON Patch from previous version
  changedBy*:   String
  changedAt*:   Timestamp
  changeReason: String
}
```

**Indexes:**
- Unique: `id`
- Unique: `(subjectId, version)`
- Lookup: `subjectId` — all versions for entity/relationship
- Filter: `changedAt` — time-travel queries

---

## Referential integrity rules (enforced at application layer)

1. `Relationship.fromEntityId` and `toEntityId` must reference active Entities.
2. `Evidence.subjectId` must reference an existing Entity or Relationship.
3. `Provenance.subjectId` must reference an existing Entity or Relationship (unique).
4. `TrustScore.subjectId` must reference an existing Entity or Relationship (unique).
5. Soft-deleting an Entity (`isActive = false`) cascades to all attached Relationships.
6. No hard deletes on any table. Hard delete is prohibited by policy.
7. `Relationship.fromEntityId ≠ Relationship.toEntityId` — no self-loops.

---

## Canonical enumerations

```
EntityType:          PERSON | PROJECT | GOAL | TASK | SKILL | DOCUMENT
                   | ORGANIZATION | EVENT | CONCEPT | ARTIFACT | LOCATION | PRODUCT

VerificationState:   UNVERIFIED | INFERRED | VERIFIED | DISPUTED

Direction:           DIRECTED | BIDIRECTIONAL

SubjectType:         ENTITY | RELATIONSHIP

EvidenceSourceType:  MEMORY | DOCUMENT | INFERENCE | USER_INPUT | SYSTEM
```

---

## Physical schema (Phase 2)
Deferred. Storage backend TBD via Phase 2 ADR (DEC-0002: ports-and-adapters).
Physical schema choices — Cypher/SQL DDL/document model — depend on the backend selected.
All logical constraints above must be honored by the chosen physical implementation.

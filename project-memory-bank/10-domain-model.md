# 10 — Domain Model

**Status:** Phase 1 — complete (2026-06-23).

## Overview
Six core objects constitute the domain. Expressed in language-agnostic pseudo-schema
(field: Type). Maps cleanly to any target language in Phase 2 (see DEC-0001).

## Object interaction map
```
Evidence ──attaches-to──► Entity ◄──from── Relationship ──to──► Entity
    │                        │                   │
    └─────────────────────► Provenance ◄──────────┘
                                │
                           TrustScore    Version (immutable snapshot)
```

---

## 1. Entity
The fundamental node. A distinct, persistent, real-world or conceptual thing.

```
Entity {
  id:                UUID                  -- globally unique, immutable
  type:              EntityType            -- from taxonomy (12-knowledge-graph-model)
  name:              String                -- canonical display name
  aliases:           String[]              -- alternate names / IDs
  attributes:        Map<String, Any>      -- type-specific structured data
  confidence:        Float [0.0, 1.0]      -- overall trustworthiness (computed)
  verificationState: VerificationState     -- UNVERIFIED | INFERRED | VERIFIED | DISPUTED
  sourceMemoryIds:   UUID[]                -- SCP Memory Core record references
  labels:            String[]              -- free-form tags
  version:           Int                   -- current version counter (starts at 1)
  createdAt:         Timestamp
  updatedAt:         Timestamp
  isActive:          Boolean               -- soft-delete flag
}
```

**Invariants:**
- `id` is assigned at creation and never changed.
- `confidence` is always recomputed from Evidence; never set manually.
- Every entity MUST have at least one Evidence record.
- Every entity MUST have exactly one Provenance record.
- `isActive = false` soft-deletes; hard deletion is prohibited.

---

## 2. Relationship
A directed, typed, evidence-backed link between two Entities.

```
Relationship {
  id:                UUID
  type:              RelationshipType      -- from taxonomy (12-knowledge-graph-model)
  fromEntityId:      UUID                  -- source Entity
  toEntityId:        UUID                  -- target Entity
  direction:         Direction             -- DIRECTED | BIDIRECTIONAL
  attributes:        Map<String, Any>
  confidence:        Float [0.0, 1.0]
  verificationState: VerificationState
  evidence:          UUID[]                -- ≥1 Evidence IDs
  provenanceId:      UUID
  strength:          Float [0.0, 1.0]      -- optional semantic weight
  version:           Int
  createdAt:         Timestamp
  updatedAt:         Timestamp
  isActive:          Boolean
}
```

**Invariants:**
- `fromEntityId ≠ toEntityId` (no self-loops).
- Both referenced entities must be active.
- Soft-deleting an entity soft-deletes all attached relationships.
- `direction = DIRECTED` by default; BIDIRECTIONAL must be explicit.

---

## 3. Evidence
A verifiable source record supporting an Entity or Relationship.

```
Evidence {
  id:                UUID
  subjectType:       SubjectType           -- ENTITY | RELATIONSHIP
  subjectId:         UUID
  sourceType:        EvidenceSourceType    -- MEMORY | DOCUMENT | INFERENCE | USER_INPUT | SYSTEM
  sourceId:          String                -- ID in the source system
  content:           String                -- verbatim or extracted snippet (max 4096 chars)
  confidence:        Float [0.0, 1.0]      -- confidence from this source
  extractedAt:       Timestamp
  extractorId:       String                -- agent/process that produced this
  verificationState: VerificationState
  metadata:          Map<String, Any>
}
```

**Invariants:**
- Immutable after creation. Corrections add a new Evidence record, not edits.
- `(subjectId, sourceId)` is unique — enforces idempotent ingestion.
- `content` is verbatim; summarization is tracked in `metadata`.

---

## 4. Provenance
Chain of custody for a fact. One record per Entity or Relationship.

```
Provenance {
  id:                UUID
  subjectType:       SubjectType
  subjectId:         UUID                  -- unique constraint
  origin:            String                -- source system (e.g., "scp-memory-core")
  extractionMethod:  String                -- "memory_extraction" | "manual" | "inference"
  transformations:   TransformationStep[]  -- ordered processing steps
  rawSourceRef:      String                -- pointer to original raw record
  sessionId:         UUID
  agentId:           String
  timestamp:         Timestamp
}

TransformationStep {
  step:              String
  appliedAt:         Timestamp
  appliedBy:         String
}
```

**Invariant:** One Provenance record per Entity/Relationship (enforced by unique constraint on `subjectId`).

---

## 5. TrustScore
Computed confidence measurement. Read-only; never set directly.

```
TrustScore {
  id:                UUID
  subjectId:         UUID                  -- unique — one active score per subject
  score:             Float [0.0, 1.0]
  components: {
    evidenceWeight:    Float               -- weighted avg of evidence confidence
    freshnessDecay:    Float               -- age-based decay factor
    verificationBonus: Float               -- bonus for VERIFIED state
    conflictPenalty:   Float               -- penalty for DISPUTED evidence
    evidenceCount:     Int
  }
  computedAt:        Timestamp
  algorithm:         String                -- versioned algorithm ID
}
```

**Scoring formula:**
```
score = clamp(
    (evidenceWeight    × 0.50)
  + (freshnessDecay    × 0.20)
  + (verificationBonus × 0.20)
  - (conflictPenalty   × 0.10)
, 0.0, 1.0)
```

---

## 6. Version
Immutable snapshot of an Entity or Relationship at a point in time.

```
Version {
  id:                UUID
  subjectType:       SubjectType
  subjectId:         UUID
  version:           Int                   -- monotonically increasing from 1
  snapshot:          Any                   -- full object at this version
  diff:              Any                   -- JSON Patch from previous version
  changedBy:         String
  changedAt:         Timestamp
  changeReason:      String
}
```

**Invariants:**
- Versions are append-only. Past versions are never mutated.
- Every mutation creates a new Version before applying the write.
- `version = 1` is the creation snapshot.

---

## Shared enumerations

```
EntityType:          PERSON | PROJECT | GOAL | TASK | SKILL | DOCUMENT
                   | ORGANIZATION | EVENT | CONCEPT | ARTIFACT | LOCATION | PRODUCT

RelationshipType:    [full catalog in 12-knowledge-graph-model.md]

VerificationState:   UNVERIFIED | INFERRED | VERIFIED | DISPUTED

Direction:           DIRECTED | BIDIRECTIONAL

SubjectType:         ENTITY | RELATIONSHIP

EvidenceSourceType:  MEMORY | DOCUMENT | INFERENCE | USER_INPUT | SYSTEM
```

---

## Knowledge lifecycle
```
Raw Memory → Extract Evidence → Resolve Entity (or create) → Attach Provenance
          → Compute TrustScore → Create Version snapshot → Emit KnowledgeUpdatedEvent
```

# 05 — Technical Decisions

Running decision log. Lightweight records here; full ADRs live under `docs/adr/` once
Phase 1 begins. Each entry: ID, status, context, decision, consequences.

---

## DEC-0001 — Implementation language deferred (stay neutral in Phase 1)
- **Status:** Accepted (explicit deferral)
- **Date:** 2026-06-23
- **Context:** Phase 1 is domain modeling and is documentation-only. Committing to a
  language now would bias conceptual modeling toward a runtime prematurely.
- **Decision:** Keep Phase 1 language-neutral. Defer the implementation language choice
  to Phase 2 (Storage Foundation), to be ratified by an ADR.
- **Consequences:** Domain model is expressed in language-agnostic terms (concepts,
  fields, invariants), translatable to any target. Slight extra step in Phase 2.

---

## DEC-0002 — Storage-agnostic repository interface; backend deferred
- **Status:** Accepted (explicit deferral)
- **Date:** 2026-06-23
- **Context:** The master prompt prioritizes future portability and simplicity. Binding
  the domain model to a specific store (native graph DB vs. Postgres vs. other) now would
  couple semantics to a backend.
- **Decision:** Design toward a **ports-and-adapters** boundary: define a storage-agnostic
  repository interface in the domain layer. Choose the concrete backend via ADR in Phase 2.
- **Consequences:** Domain model and storage are decoupled; backend can change without
  rewriting semantics. Requires a clean repository abstraction and at least one adapter
  in Phase 2.

---

---

## DEC-0003 — Entity taxonomy: 12 canonical types with JSON attributes
- **Status:** Accepted (Phase 1)
- **Date:** 2026-06-23
- **Context:** A bounded, well-defined taxonomy is required for reliable identity resolution
  and relationship constraint enforcement. See ADR-0001.
- **Decision:** 12 entity types (PERSON, PROJECT, GOAL, TASK, SKILL, DOCUMENT, ORGANIZATION,
  EVENT, CONCEPT, ARTIFACT, LOCATION, PRODUCT). Type-specific attributes in `attributes: JSON`.
- **Consequences:** All ingestion adapters must classify to one of these 12. New types require
  a new ADR.

---

## DEC-0004 — Relationship typing: 36 types, 8 categories, directed by default
- **Status:** Accepted (Phase 1)
- **Date:** 2026-06-23
- **Context:** Relationships are first-class. Untyped or free-form edges lose semantic meaning
  in traversals. See ADR-0002.
- **Decision:** 36 relationship types across 8 semantic categories (IDENTITY, OWNERSHIP,
  DEPENDENCY, HIERARCHY, TEMPORAL, GOAL, PROJECT, SEMANTIC). All directed by default;
  bidirectionality is explicit. Entity-type constraints enforced at application layer.
- **Consequences:** Adapters must map extracted relationships to known types. Unknown
  relationships default to SEMANTIC.RELATED_TO with reduced confidence.

---

## DEC-0005 — Evidence: separate immutable records; Provenance: one per subject
- **Status:** Accepted (Phase 1)
- **Date:** 2026-06-23
- **Context:** Auditability demands that sourced facts can never be silently overwritten.
  See ADR-0003.
- **Decision:** Evidence is stored as separate, immutable records (one per source per
  subject). Corrections add new records. Provenance is one record per subject (unique
  on `subjectId`), extensible via ordered `TransformationStep` list.
- **Consequences:** Every write creates an Evidence record. Conflict detection is
  evidence-level comparison. Efficient fetch requires indexed `(subjectType, subjectId)`.

---

## DEC-0006 — Versioning: append-only Version log; current state in live record
- **Status:** Accepted (Phase 1)
- **Date:** 2026-06-23
- **Context:** Knowledge evolves. Time-travel, audit history, and conflict traceability
  are first-class requirements. See ADR-0004.
- **Decision:** Every Entity/Relationship write inserts a Version record (full snapshot +
  JSON Patch diff) before mutating the live record. Versions are immutable and never deleted.
  Current state is always the live record (no replay required for reads).
- **Consequences:** 2 DB writes per mutation (inside a transaction). Storage grows
  unbounded for high-churn entities; Phase 9 compaction policy to address at scale.

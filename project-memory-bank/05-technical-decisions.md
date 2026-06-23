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

_Next decisions (Phase 1) will cover: entity taxonomy boundaries, relationship typing
model, evidence/provenance representation, and versioning strategy._

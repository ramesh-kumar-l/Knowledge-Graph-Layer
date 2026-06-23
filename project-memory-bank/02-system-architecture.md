# 02 — System Architecture (High Level)

## Position in SCP
The Knowledge Graph Layer is built **incrementally on top of existing, stable SCP
foundations**. It does not redesign or replace them.

```
            ┌─────────────────────────────────────────────┐
            │            Knowledge Graph Layer             │  ← this project
            │  Entities · Relationships · Evidence ·       │
            │  Provenance · Trust · Query · Visualization  │
            └─────────────────────────────────────────────┘
                              ▲ builds on
   ┌───────────┬───────────┬───────────┬───────────┬──────────────┐
   │ Memory    │ Trust     │ Retrieval │ SDK       │ Observability │  ← existing SCP
   │ Core      │ Foundation│ Foundation│ Foundation│ Foundation    │     (stable)
   └───────────┴───────────┴───────────┴───────────┴──────────────┘
```

## Conceptual layers (this project)
1. **Domain model** — Entity, Relationship, Evidence, Provenance (Phase 1).
2. **Storage foundation** — repositories + versioning behind a storage-agnostic
   interface (Phase 2).
3. **Entity engine** — extraction, normalization, deduplication, scoring (Phase 3).
4. **Relationship engine** — extraction, discovery, evidence linking, validation (Phase 4).
5. **Query engine** — traversal, path discovery, semantic + trust-aware retrieval (Phase 5).
6. **Trust integration** — scoring, evidence resolution, explainability (Phase 6).
7. **Visualization & platform** — UI modules, REST/SDK, hardening (Phases 7–9).

## Deliberately undecided in Phase 1
- **Implementation language:** intentionally deferred (see DEC-0001). Phase 1 stays
  language-neutral and conceptual.
- **Storage backend:** intentionally deferred (see DEC-0002). Design favors a
  **storage-agnostic repository / ports-and-adapters boundary** so the concrete backend
  (native graph DB, Postgres, or other) can be chosen via ADR in Phase 2 without
  rewriting the domain model. Honors the "future portability" principle.

## Cross-cutting principles
Reliability · Trustworthiness · Explainability · Maintainability · Extensibility ·
Simplicity · Scalability. Trust metadata and observability are first-class, not add-ons.

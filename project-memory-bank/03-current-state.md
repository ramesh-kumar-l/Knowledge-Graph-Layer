# 03 — Current State

**As of:** 2026-06-23

## Status
**Phase 1 — Domain Model complete.** No implementation code exists yet.

## Repository structure

```
project-memory-bank/       -- single source of truth (all phases)
docs/
  adr/
    ADR-0001-entity-taxonomy.md
    ADR-0002-relationship-typing.md
    ADR-0003-evidence-provenance.md
    ADR-0004-versioning-strategy.md
README.md
```

## What exists

### Domain model (Phase 1 — complete)
- `10-domain-model.md` — Entity, Relationship, Evidence, Provenance, TrustScore, Version
- `11-memory-model.md` — SCP Memory Core ingestion pipeline and mapping rules
- `12-knowledge-graph-model.md` — 12 entity types + 36 relationship types (8 categories)
- `13-query-model.md` — 6 query types with result envelopes and global parameters
- `14-trust-model.md` — Confidence scoring formula, verification states, conflict detection
- `22-graph-schema.md` — Logical schema for all 5 records (Entity, Relationship, Evidence, Provenance, TrustScore, Version)
- `docs/adr/ADR-0001` through `ADR-0004` — Entity taxonomy, relationship typing, evidence/provenance, versioning

### Foundation docs (Phase 0 — complete)
- Vision, product thesis, system architecture, roadmap, technical decisions

## What does NOT exist yet
- Any implementation code, tests, storage layer, or APIs.
- Physical schema (DDL, Cypher) — Phase 2.
- Entity/relationship extraction engines — Phase 3/4.
- Query engine — Phase 5.
- Trust scoring engine — Phase 6.
- UI — Phase 7.

## Next
Awaiting explicit approval to begin **Phase 2 — Storage Foundation**.
See `33-next-actions.md`.

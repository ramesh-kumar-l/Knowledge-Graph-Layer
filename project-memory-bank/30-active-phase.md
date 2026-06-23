# 30 — Active Phase

**Current phase:** Phase 1 — Domain Model → **complete**.

**Status:** Full domain model designed and documented. Awaiting **explicit approval** to begin Phase 2.

## Completed this phase
- Core domain objects: Entity, Relationship, Evidence, Provenance, TrustScore, Version.
- Entity taxonomy: 12 canonical types with attribute schemas.
- Relationship taxonomy: 36 types across 8 semantic categories.
- Memory ingestion model: SCP Memory Core → KG pipeline.
- Trust model: confidence formula, verification states, conflict detection.
- Logical graph schema: all 5 record types with indexes and constraints.
- Query model: 6 query types with result envelopes.
- ADRs: DEC-0003 through DEC-0006.

## Boundary
- Do NOT begin Phase 2 (Storage Foundation) until the user approves.
- No implementation code, DDL, or running services exist yet.

## Next phase
Phase 2 — Storage Foundation. See `04-roadmap.md` and `33-next-actions.md`.

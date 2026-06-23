# 21 — Storage Design

**Status:** Not started — Phase 2 deliverable.

## Purpose
Define persistence: schema, repositories, versioning, and migration strategy.

## Direction (from DEC-0002)
- **Storage-agnostic by design.** The domain layer depends on a repository interface
  (ports-and-adapters), not on a specific database.
- The concrete backend (native graph DB, Postgres, or other) is **deferred** and will be
  chosen via an ADR in Phase 2.
- Storage must support: graph traversal, metadata filtering, hybrid retrieval, version
  history, trust metadata, and explainability metadata.

## To be defined in Phase 2
- Repository interface definition.
- Concrete backend selection (ADR) + first adapter.
- Versioning and migration strategy.

_(Placeholder — no concrete schema yet.)_

# 33 — Next Actions

Phase 1 is complete. Awaiting approval for Phase 2.

## On approval: begin Phase 2 — Storage Foundation

Phase 2 deliverables (all require implementation code for the first time):

1. **Choose implementation language** — ADR to ratify (DEC-0001 deferred this to Phase 2).
   Recommended: Python (FastAPI / Pydantic) for rapid iteration and rich graph library ecosystem.
2. **Choose storage backend** — ADR to ratify (DEC-0002 deferred this). Options:
   - Neo4j / Memgraph (native graph; optimal for traversals)
   - PostgreSQL + pgvector (relational + vector; operationally familiar)
   - ArangoDB (multi-model; graph + document)
3. **Physical schema** — DDL or Cypher scripts for all 6 record types.
4. **Repository interfaces** — storage-agnostic ports (DEC-0002 pattern).
5. **Repository adapters** — concrete implementation for chosen backend.
6. **CRUD APIs** — entity/relationship create, read, update, soft-delete.
7. **Versioning enforcement** — transaction-wrapped version-before-write.
8. **Migration strategy** — schema migration tooling and runbook.
9. **Unit + integration tests** — all repository operations covered.

## File structure created in Phase 2
```
src/
  domain/          -- pure domain models (from Phase 1 pseudo-schema)
  repositories/    -- abstract repository interfaces (ports)
  adapters/        -- concrete storage adapters
  migrations/      -- schema migration scripts
tests/
  unit/
  integration/
```

_Do not proceed without explicit user approval (phase-execution model)._

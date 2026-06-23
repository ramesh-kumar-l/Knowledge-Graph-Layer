# ADR-0006 — Storage Backend: PostgreSQL + pgvector

**Date:** 2026-06-23
**Status:** Accepted
**Deciders:** SCP Knowledge Graph Team

---

## Context

DEC-0002 mandated a ports-and-adapters (storage-agnostic) repository boundary.
Phase 2 must ratify a concrete storage backend. Candidates evaluated:

1. **Neo4j / Memgraph** — native graph; optimal for deep traversal
2. **PostgreSQL + pgvector** — relational + vector; operationally familiar
3. **ArangoDB** — multi-model (graph + document)

Phase 2 needs: ACID transactions (required for transactional versioning in DEC-0006),
JSONB for flexible attributes, vector similarity for Phase 5 semantic search, and
a single deployment unit.

---

## Decision

**Primary backend:** PostgreSQL 16+ with pgvector extension.
**Graph traversal:** Recursive CTEs (sufficient for depth ≤ 5; re-evaluate at Phase 5).
**Vector similarity:** pgvector for embedding-based semantic search (Phase 5).
**Connection pooling:** asyncpg + SQLAlchemy async session.

---

## Rationale

| Criterion | PostgreSQL + pgvector | Neo4j | ArangoDB |
|-----------|----------------------|-------|----------|
| ACID transactions | Full | Full | Full |
| Transactional versioning (DEC-0006) | CTE-in-transaction | Supported | Supported |
| JSONB flexible attributes | Native JSONB | Properties | Document |
| Vector similarity (Phase 5) | pgvector | No | Approximated |
| Operational complexity | Low (single process) | High (JVM + Bolt) | Medium |
| Recursive graph traversal | Recursive CTEs | Cypher MATCH | AQL graph traversal |
| Managed cloud options | RDS, Cloud SQL, Supabase | Neo4j Aura | ArangoDB Cloud |

The critical insight: our graph is moderately deep (≤ 5 hops in Phase 5) but
the primary query patterns are point lookups and 1–2 hop traversals. PostgreSQL
recursive CTEs handle this efficiently. A native graph DB becomes compelling
only if traversal depth routinely exceeds 5 hops — a Phase 5/6 re-evaluation trigger.

---

## Storage schema approach

- 6 relational tables: `entities`, `relationships`, `evidence`, `provenance`,
  `trust_scores`, `versions`
- JSONB columns for `attributes`, `metadata`, `snapshot`, `diff`, `transformations`
- UUID primary keys throughout
- All constraints from `22-graph-schema.md` enforced at application layer
- Physical indexes: specified in `migrations/versions/001_initial_schema.py`

---

## Re-evaluation trigger

Migrate to a native graph DB if:
- Graph traversal queries at depth > 5 represent > 20% of query volume, OR
- p99 traversal latency exceeds 500ms at production scale

---

## Consequences

- **Positive:** Single deployment unit; no JVM or graph-specific ops expertise needed.
- **Positive:** pgvector provides Phase 5 semantic search without adding a service.
- **Positive:** Standard PostgreSQL tooling (pg_dump, pgBouncer, logical replication).
- **Negative:** Deep multi-hop traversals (> 5 hops) require recursive CTE optimization.
- **Neutral:** ports-and-adapters boundary means swapping to Neo4j later requires only
  a new adapter — domain and service layers are unaffected.

# 33 — Next Actions

Phase 4 is complete. Awaiting approval for Phase 5.

## On approval: begin Phase 5 — Query Engine

Phase 5 adds traversal, semantic similarity search, and pgvector embeddings.

### Phase 5 deliverables

1. **Graph traversal service** (`src/services/graph_traversal_service.py`)
   - Depth-N traversal from a root entity (default depth 3)
   - Direction filter: outbound / inbound / both
   - Relationship type filter
   - p99 < 200ms target (SQLite test, PostgreSQL production)

2. **Query router** (`src/api/routers/query.py`)
   - `GET /v1/entities/{id}/graph` — subgraph up to depth N
   - `GET /v1/entities/{id}/neighbors` — direct relationships
   - `GET /v1/entities/search` — name search with type filter
   - `GET /v1/entities/{id}/path/{to_id}` — shortest path between two entities

3. **pgvector semantic search** (Phase 5b, if embedding API available)
   - `GET /v1/entities/similar` — vector similarity search
   - Embedding generation deferred to external call (OpenAI/Anthropic API)

4. **Tests** — unit + integration:
   - Traversal at depth 1, 2, 3 from fixture graphs
   - Circular graph (no infinite loop)
   - Path between connected + disconnected entities
   - Search by name substring

### Phase 5 file structure
```
src/
  services/
    graph_traversal_service.py   (< 200 lines)
  api/
    routers/
      query.py                   (< 150 lines)
```

### Phase 5 exit criteria
- Depth-3 traversal returns correct subgraph; circular references handled.
- All 6 query types from 13-query-model.md implemented (or documented as deferred).
- p99 < 200ms on depth-3 traversal against 1k-node SQLite fixture.
- ≥80% coverage maintained.

_Do not proceed without explicit user approval (phase-execution model)._

# 13 — Query Model

**Status:** Phase 1 — foundations complete (2026-06-23); full engine implemented in Phase 5.

## Overview
Six query types cover the full retrieval surface of the Knowledge Graph.
All return results through a common `QueryResult<T>` envelope.

---

## Query types

### 1. Point lookup
Retrieve a single Entity or Relationship by ID.
```
PointLookup {
  subjectType:      ENTITY | RELATIONSHIP
  id:               UUID
  includeEvidence?: Boolean     (default false)
  includeHistory?:  Boolean     (default false)
  asOf?:            Timestamp   (time-travel; default now)
}
```

### 2. Entity search
Search by name, alias, type, or attribute value.
```
EntitySearch {
  name?:              String            (exact | prefix | fuzzy)
  type?:              EntityType[]
  labels?:            String[]
  minConfidence?:     Float             (default 0.0)
  verificationState?: VerificationState[]
  createdAfter?:      Timestamp
  updatedAfter?:      Timestamp
  limit:              Int               (default 20, max 100)
  offset:             Int               (default 0)
}
```

### 3. Graph traversal
Walk the graph from a starting entity along edges.
```
GraphTraversal {
  startEntityId:       UUID
  relationshipTypes?:  RelationshipType[]   (filter edge types; empty = all)
  direction:           OUTBOUND | INBOUND | BOTH
  maxDepth:            Int                  (default 2, max 5)
  minConfidence?:      Float
  includeEvidence?:    Boolean
  limit?:              Int                  (max nodes returned)
}

Returns: GraphResult {
  nodes:      Entity[]
  edges:      Relationship[]
  truncated:  Boolean
}
```

### 4. Path discovery
Find paths between two entities.
```
PathDiscovery {
  fromEntityId:        UUID
  toEntityId:          UUID
  maxHops:             Int          (default 4, max 8)
  minConfidence?:      Float
  relationshipTypes?:  RelationshipType[]
  rankBy:              "SHORTEST" | "HIGHEST_TRUST" | "MOST_EVIDENCE"
  limit:               Int          (number of paths; default 3, max 10)
}

Returns: PathResult {
  paths:   Path[]
  meta: { totalFound: Int, truncated: Boolean }
}

Path {
  entities:          Entity[]
  relationships:     Relationship[]
  totalConfidence:   Float          -- min(confidence across all hops)
  hopCount:          Int
}
```

### 5. Trust-filtered query
Composable filter applied to any other query type.
```
TrustFilter {
  minScore?:          Float
  requireVerified?:   Boolean
  fresherThan?:       Duration      -- e.g., "30d", "90d"
  excludeDisputed?:   Boolean
  minEvidenceCount?:  Int
}
```
TrustFilter composes orthogonally with all query types above.
Example: `EntitySearch + TrustFilter` returns only high-confidence entities.

### 6. Semantic similarity search  *(Phase 5 — stub)*
Find entities semantically similar to a text query or reference entity.
```
SemanticSearch {
  query?:              String         (text)
  referenceEntityId?:  UUID
  type?:               EntityType[]
  minSimilarity?:      Float          (default 0.7)
  limit:               Int
}
```
Embedding / vector support is a Phase 5 concern. Defined here to reserve the
contract surface; implementation returns `NOT_IMPLEMENTED` until Phase 5.

---

## Common result envelope

All queries return:
```
QueryResult<T> {
  data:        T[]
  total:       Int
  offset:      Int
  limit:       Int
  truncated:   Boolean
  queryId:     UUID          -- for audit / observability correlation
  executedAt:  Timestamp
  meta:        QueryMeta
}

QueryMeta {
  planType:    String        -- "point_lookup" | "traversal" | "path" | "search" | "semantic"
  durationMs:  Int
  nodeCount:   Int           -- populated for graph results
  edgeCount:   Int
}
```

---

## Global query parameters

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `minConfidence` | Float | 0.5 | Filter results below threshold |
| `includeInactive` | Boolean | false | Include soft-deleted entities |
| `asOf` | Timestamp | now() | Time-travel to a past snapshot |
| `maxDepth` | Int | 2 | Traversal depth cap |
| `includeEvidence` | Boolean | false | Attach Evidence to results |
| `includeProvenance` | Boolean | false | Attach Provenance to results |
| `includeTrustScore` | Boolean | false | Attach TrustScore to results |

---

## Ranking

Default ranking for list results:
```
rank = (confidence × 0.5) + (freshness × 0.3) + (evidenceCount_normalized × 0.2)
```
`sortBy` parameter overrides ranking (e.g., `sortBy: "updatedAt DESC"`).

---

## Access control (design intent)
All query results are filtered by the caller's authorization scope.
Full policy is defined in Phase 2 (security model). Core rule:
a query never returns an unauthorized entity, even if it lies in a traversal path —
the path is truncated at the authorization boundary.

---

## Observability requirements
Every query MUST emit a `knowledge.query_executed` event with:
`queryId`, `planType`, `durationMs`, `nodeCount`, `callerAgentId`, `minConfidence`.

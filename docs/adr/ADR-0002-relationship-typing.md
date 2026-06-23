# ADR-0002 — Relationship Typing Model

**Status:** Accepted  
**Date:** 2026-06-23  
**Phase:** 1 — Domain Model

---

## Context

Relationships are first-class facts in the knowledge graph. Without a disciplined
relationship taxonomy:
- Traversal queries become meaningless (too many disconnected edge types).
- Entity-type constraints can't be enforced (no schema violations detectable).
- Trust and evidence can't attach to edges consistently.

Key tension: too few relationship types loses semantic meaning; too many creates
maintenance burden and inconsistent classification.

---

## Decision

Adopt **36 canonical relationship types** across **8 semantic categories**:

| Category | Types |
|----------|-------|
| IDENTITY | IS_SAME_AS, IS_ALIAS_OF, IS_VARIATION_OF |
| OWNERSHIP | OWNS, CREATED_BY, MAINTAINED_BY, AUTHORED_BY |
| DEPENDENCY | DEPENDS_ON, REQUIRES, USES, INTEGRATES_WITH |
| HIERARCHY | PART_OF, CONTAINS, CHILD_OF, PARENT_OF |
| TEMPORAL | PRECEDED_BY, FOLLOWED_BY, CO_OCCURRED_WITH, SCHEDULED_ON |
| GOAL | WORKS_TOWARD, CONTRIBUTES_TO, BLOCKS, ENABLES |
| PROJECT | ASSIGNED_TO, MEMBER_OF, REPORTS_TO, COLLABORATES_ON |
| SEMANTIC | RELATED_TO, SIMILAR_TO, CONTRADICTS, REFERENCES, DERIVED_FROM |

Every relationship is **directed by default** (`Direction = DIRECTED`).
Bidirectional edges must be declared explicitly in the type definition.

---

## Entity-type constraints (enforcement matrix excerpt)

| Relationship | Valid from | Valid to |
|-------------|------------|---------|
| ASSIGNED_TO | TASK | PERSON |
| AUTHORED_BY | DOCUMENT, ARTIFACT | PERSON |
| WORKS_TOWARD | TASK, PROJECT | GOAL |
| REPORTS_TO | PERSON | PERSON |
| IS_SAME_AS | Any EntityType | Same EntityType |
| DEPENDS_ON | ARTIFACT, PRODUCT, PROJECT | ARTIFACT, PRODUCT, PROJECT |
| MEMBER_OF | PERSON | PROJECT, ORGANIZATION |
| BLOCKS | TASK, PROJECT, GOAL | TASK, PROJECT, GOAL |
| CO_OCCURRED_WITH | EVENT, TASK | EVENT, TASK |

Violations must be rejected at the application layer on write (not silently stored).

---

## Rationale

- **Semantic grouping into 8 categories** enables category-level traversal filters
  ("show me only DEPENDENCY relationships") without exposing all 36 types.
- **Directed by default** avoids ambiguity. Bidirectionality is always a deliberate design
  choice and must be declared.
- **Constraint enforcement at application layer** (not DB layer) keeps the schema
  backend-agnostic while still protecting data integrity.
- **`strength: Float [0.0, 1.0]`** on each relationship captures semantic weight
  independent of confidence (e.g., a verified but weak RELATED_TO relationship).

---

## Consequences

- Ingestion adapters must map every extracted relationship to one of the 36 types.
- Unknown or unmappable relationships are stored as SEMANTIC.RELATED_TO with
  `confidence` lowered to reflect the loose classification.
- Adding a new relationship type requires a new ADR; no ad hoc types.
- The constraint matrix must be maintained alongside the taxonomy as types evolve.

---

## Rejected alternatives

| Option | Reason rejected |
|--------|-----------------|
| Free-form string labels on edges | No schema enforcement; inconsistent traversal |
| RDF / OWL-style predicate URIs | Too verbose; over-engineered for this use case |
| Single "RELATED_TO" for all edges | Loses all semantic meaning in traversals |
| User-defined relationship types | Deferred to Phase 3+ extensibility model |

# ADR-0001 — Entity Taxonomy Boundaries

**Status:** Accepted  
**Date:** 2026-06-23  
**Phase:** 1 — Domain Model

---

## Context

The Knowledge Graph Layer must classify all real-world and conceptual things it tracks.
Without a bounded taxonomy, entity classification becomes inconsistent across ingestion
sources, making identity resolution and relationship validation unreliable.

Key tensions:
- **Too few types** — forces overloading (e.g., one type for both humans and companies).
- **Too many types** — increases maintenance burden and complicates cross-type queries.
- **Domain-specific types now** — risks locking in types that don't generalize.

---

## Decision

Adopt **12 canonical entity types** — no more, no less in Phase 1:

```
PERSON | PROJECT | GOAL | TASK | SKILL | DOCUMENT
ORGANIZATION | EVENT | CONCEPT | ARTIFACT | LOCATION | PRODUCT
```

These 12 types cover the full surface area of the SCP use case (people, work,
knowledge, places, time, outputs) without over-specializing.

Type-specific structured data lives in the `attributes` field (schema-on-write, JSON)
rather than in separate tables per type, keeping the schema extensible without
DDL changes.

---

## Rationale

- **Coverage:** 12 types map cleanly to all expected Memory Core content (user facts,
  project records, documents, technical artifacts, events, organizations, locations).
- **Extensibility:** `attributes: JSON` absorbs type-specific fields without schema changes.
  New attribute shapes can be defined in Phase 3+ without adding entity type columns.
- **Identity resolution:** Homogeneous identity matching (name + type) is simpler and
  more reliable when the type space is bounded. Unbounded types make similarity functions
  ambiguous.
- **Precedent:** The 12 types align with common knowledge graph standards
  (Wikidata types, schema.org Thing taxonomy) while staying SCP-specific.

---

## Consequences

- All ingestion adapters must classify every memory record to one of the 12 types.
- A classification confidence score accompanies every entity on creation.
- If a future domain requires a new type, it is added via a new ADR — not ad hoc.
- Type constraints on relationships (e.g., ASSIGNED_TO: TASK → PERSON only) are
  validated at the application layer (see ADR-0002).

---

## Rejected alternatives

| Option | Reason rejected |
|--------|-----------------|
| Single generic "Node" type with free-form labels | Loses type-safety, makes relationship constraints impossible |
| Per-industry domain-specific types (30+) | Over-specialization; doesn't generalize; maintenance burden |
| Dynamic / user-defined types | Deferred to Phase 3+ plugin model; too complex for Phase 1 |

---

## Review trigger

Revisit this ADR if: a new SCP use case requires a type that cannot be cleanly modeled
as one of the 12 + attributes, OR if attribute heterogeneity for a type exceeds 80% nulls
across 5+ fields (signal that a type split is warranted).

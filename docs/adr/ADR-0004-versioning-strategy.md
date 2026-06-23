# ADR-0004 — Versioning Strategy

**Status:** Accepted  
**Date:** 2026-06-23  
**Phase:** 1 — Domain Model

---

## Context

Knowledge evolves. Facts change, entities are enriched, relationships are corrected.
The system must support:
1. Full audit history — what did we believe, and when?
2. Time-travel queries — query the graph at a past point in time.
3. Safe mutation — updates must not destroy prior state.
4. Conflict traceability — disputed facts need historical comparison.

---

## Decision

**Append-only versioning via a dedicated Version log.**

Every Entity and Relationship write (create or update) MUST:
1. Write a `Version` record with the full object snapshot and a JSON Patch diff.
2. Increment the `version` counter on the entity/relationship.
3. Only then apply the mutation to the live record.

Rules:
- `version = 1` is the creation snapshot.
- Version numbers are monotonically increasing integers (no gaps).
- Version records are **never mutated or deleted**.
- Soft-delete (`isActive = false`) creates a new version with `changeReason = "soft_delete"`.
- Time-travel is achieved by replaying versions to any point via the `asOf` query parameter.

---

## Rationale

- **Separate Version log** (not event sourcing): keeps the live read path simple (no
  replay needed for current state) while preserving full history. This is appropriate for
  a knowledge graph where current state is queried far more than historical state.
- **JSON Patch diff** alongside the full snapshot: enables efficient "what changed"
  queries without full snapshot comparison, while keeping the snapshot available for
  standalone replay.
- **Append-only, never delete**: mandatory for auditability. Regulators and users alike
  must be able to trace every mutation.
- **Version as Int, not timestamp**: timestamps can collide under high concurrency;
  monotonic integers are unambiguous orderings.

---

## Write sequence (enforced at repository layer)

```
BEGIN TRANSACTION
  1. Read current state of entity/relationship
  2. Compute JSON Patch diff (current → new)
  3. INSERT Version_Record { snapshot: current, diff, changedBy, changedAt, changeReason }
  4. UPDATE entity/relationship with new values; increment version
COMMIT
```

The repository layer (Phase 2) must enforce this sequence inside a transaction.
No caller bypasses versioning.

---

## Consequences

- Every write is 2 DB operations (version + update) inside a transaction.
- Read for current state remains a single lookup (no replay).
- Time-travel requires version log replay; this is an acceptable trade-off given
  time-travel is an infrequent, audit-oriented access pattern.
- Storage grows unbounded for high-churn entities; a compaction policy (Phase 9)
  may be needed at scale. Snapshots beyond a configurable retention window can be
  archived but must never be deleted.

---

## Rejected alternatives

| Option | Reason rejected |
|--------|-----------------|
| Event sourcing (no live record, replay everything) | Too expensive for common current-state reads; replay latency unacceptable |
| Timestamp-based versioning | Timestamp collisions under concurrent writes; ambiguous ordering |
| Soft-delete via separate archive table | Adds complexity; breaks single-table audit queries |
| No versioning in Phase 1 (add later) | Retrofitting versioning into an existing schema is a breaking migration; must be first-class from day one |

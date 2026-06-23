# 33 — Next Actions

Phase 5 is complete. Awaiting approval for Phase 6.

## On approval: begin Phase 6 — Trust Integration

Phase 6 adds trust propagation across multi-hop paths, conflict resolution workflow,
and the `/explain/{entityId}` endpoint.

### Phase 6 deliverables

1. **Trust propagation service** (`src/services/trust_propagation_service.py`)
   - Propagate trust score changes along outbound relationships
   - Pessimistic propagation: path_confidence = min(all hop confidences)
   - Recompute downstream TrustScores when an entity or relationship score changes

2. **Conflict resolution service** (`src/services/conflict_resolution_service.py`)
   - Accept or reject conflicting evidence (`DISPUTED` → `VERIFIED` or `UNVERIFIED`)
   - Version-log all state transitions
   - Emit `KnowledgeConflictResolved` domain event

3. **Explain endpoint** (`src/api/routers/explain.py`)
   - `GET /v1/explain/{entity_id}` — full trust breakdown:
     - TrustScore components (evidenceWeight, freshnessDecay, verificationBonus, conflictPenalty)
     - Evidence records attached
     - Provenance chain
     - Conflict history if DISPUTED

4. **Trust-enriched graph traversal** — extend GraphTraversalService to optionally attach TrustScore to each returned node/edge

5. **Tests** — unit + integration:
   - Trust propagation: score change propagates 1, 2, 3 hops
   - Conflict accept/reject transitions state correctly
   - Explain endpoint returns correct components

### Phase 6 file structure
```
src/
  services/
    trust_propagation_service.py   (< 200 lines)
    conflict_resolution_service.py (< 150 lines)
  api/
    routers/
      explain.py                   (< 120 lines)
```

### Phase 6 exit criteria
- Trust propagation: score changes on entity A ripple to 3-hop downstream entities.
- Conflict resolution: DISPUTED → VERIFIED/UNVERIFIED with version log entry.
- `GET /v1/explain/{entity_id}` returns full trust breakdown JSON.
- ≥80% coverage maintained.

_Do not proceed without explicit user approval (phase-execution model)._

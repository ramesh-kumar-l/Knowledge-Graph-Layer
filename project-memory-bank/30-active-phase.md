# 30 — Active Phase

**Current phase:** Phase 6 — Trust Integration → **complete**.

**Status:** Trust propagation, conflict resolution, and explain endpoint implemented and tested. Awaiting **explicit approval** to begin Phase 7.

## Completed this phase

### Source code delivered
- `src/services/trust_propagation_service.py` — BFS outbound propagation up to max_hops (default 3); pessimistic confidence capping (min of path); per-hop relationship confidence update; TrustScore recomputation for each downstream entity; cycle-safe (visited set)
- `src/services/conflict_resolution_service.py` — DISPUTED → VERIFIED (ACCEPT) or UNVERIFIED (REJECT); version-logged before state change; TrustScore recomputed after transition; custom reason field; ConflictResolutionError for non-DISPUTED entities
- `src/api/routers/explain.py` — `GET /v1/explain/{entity_id}` returns full trust breakdown: TrustScore components, all Evidence records, Provenance chain, conflict-related version history
- `tests/unit/test_trust_propagation.py` — 9 unit tests
- `tests/unit/test_conflict_resolution.py` — 7 unit tests
- `tests/integration/test_trust_integration.py` — 11 integration tests

### Supporting changes
- `src/services/__init__.py` — exports TrustPropagationService, PropagationResult, ConflictResolutionService, ResolutionDecision, ConflictResolutionError
- `src/api/main.py` — registers explain router; version bumped to 0.4.0
- `src/api/deps.py` — trust_propagation_service() and conflict_resolution_service() DI factories added

### Exit criteria met
- [x] Trust propagation ripples 3 hops downstream (integration test: A→B→C→D)
- [x] BFS propagation is cycle-safe (visited set)
- [x] Relationship confidence capped pessimistically when path_confidence < rel.confidence
- [x] Conflict resolution: DISPUTED → VERIFIED (ACCEPT) with version log entry
- [x] Conflict resolution: DISPUTED → UNVERIFIED (REJECT) with version log entry
- [x] Non-DISPUTED entities raise ConflictResolutionError on resolve()
- [x] `GET /v1/explain/{entity_id}` returns full trust breakdown JSON (trust score, evidence, provenance, conflict history)
- [x] 404 for unknown entity on /explain
- [x] 208/208 tests passing, 90.35% coverage (≥80% threshold)

## Known limitations
- TrustPropagationService is called inline — no async event queue (Phase 9 concern)
- Relationship confidence capping is pessimistic-only (cannot increase caps after trust recovery; configurable in future)
- `GET /v1/explain` does not return downstream propagation path confidence (Phase 7 enhancement)

## Boundary
- Do NOT begin Phase 7 (Visualization) until the user approves.

## Next phase
Phase 7 — Visualization. See `33-next-actions.md`.

"""Unit tests for TrustPropagationService — BFS confidence capping, downstream recompute."""
from unittest.mock import AsyncMock, MagicMock, call
from uuid import uuid4

import pytest

from src.domain import Entity, Relationship, EntityType, RelationshipType, Direction, VerificationState
from src.services.trust_propagation_service import TrustPropagationService, PropagationResult


# ── helpers ────────────────────────────────────────────────────────────────────

def _entity(name: str = "E", confidence: float = 0.8) -> Entity:
    return Entity(
        type=EntityType.PERSON, name=name,
        confidence=confidence, verification_state=VerificationState.UNVERIFIED,
    )


def _rel(from_id, to_id, confidence: float = 0.8) -> Relationship:
    return Relationship(
        type=RelationshipType.RELATED_TO,
        from_entity_id=from_id,
        to_entity_id=to_id,
        direction=Direction.DIRECTED,
        confidence=confidence,
    )


def _make_svc(e_repo, r_repo, ts_repo=None, ts_svc=None) -> TrustPropagationService:
    return TrustPropagationService(
        entity_repo=e_repo,
        rel_repo=r_repo,
        trust_repo=ts_repo or AsyncMock(),
        trust_score_svc=ts_svc or AsyncMock(),
    )


# ── tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_propagate_unknown_source_returns_empty():
    e_repo = AsyncMock()
    e_repo.get_by_id.return_value = None
    svc = _make_svc(e_repo, AsyncMock())
    result = await svc.propagate(uuid4())
    assert result.updated_entity_ids == []
    assert result.updated_rel_ids == []
    assert result.hops_reached == 0


@pytest.mark.asyncio
async def test_propagate_no_outbound_rels_no_updates():
    source = _entity("Source", confidence=0.9)
    e_repo = AsyncMock()
    e_repo.get_by_id.return_value = source
    r_repo = AsyncMock()
    r_repo.get_outbound.return_value = []

    svc = _make_svc(e_repo, r_repo)
    result = await svc.propagate(source.id)

    assert result.updated_entity_ids == []
    assert result.updated_rel_ids == []


@pytest.mark.asyncio
async def test_propagate_1hop_updates_downstream_entity():
    source = _entity("Source", confidence=0.9)
    downstream = _entity("Downstream", confidence=0.8)
    rel = _rel(source.id, downstream.id, confidence=0.85)

    e_repo = AsyncMock()
    e_repo.get_by_id.side_effect = lambda eid: (
        source if eid == source.id else downstream
    )
    r_repo = AsyncMock()
    r_repo.get_outbound.side_effect = lambda eid, limit=500: (
        [rel] if eid == source.id else []
    )
    ts_svc = AsyncMock()

    svc = _make_svc(e_repo, r_repo, ts_svc=ts_svc)
    result = await svc.propagate(source.id, max_hops=1)

    assert downstream.id in result.updated_entity_ids
    assert result.hops_reached == 1
    ts_svc.compute_and_persist.assert_called_once()


@pytest.mark.asyncio
async def test_propagate_caps_rel_confidence_when_below_path():
    """path_confidence = min(source.conf=0.5, rel.conf=0.9) = 0.5; rel should be capped."""
    source = _entity("Source", confidence=0.5)
    downstream = _entity("Downstream", confidence=0.9)
    rel = _rel(source.id, downstream.id, confidence=0.9)

    e_repo = AsyncMock()
    e_repo.get_by_id.side_effect = lambda eid: (
        source if eid == source.id else downstream
    )
    r_repo = AsyncMock()
    r_repo.get_outbound.side_effect = lambda eid, limit=500: (
        [rel] if eid == source.id else []
    )

    svc = _make_svc(e_repo, r_repo)
    await svc.propagate(source.id, max_hops=1)

    # rel.confidence (0.9) > path_conf (0.5), so update_confidence should be called
    r_repo.update_confidence.assert_called_once_with(rel.id, 0.5, "trust-propagation")


@pytest.mark.asyncio
async def test_propagate_no_cap_when_rel_already_below_path():
    """If rel.confidence <= path_confidence, no update_confidence call."""
    source = _entity("Source", confidence=0.9)
    downstream = _entity("Downstream", confidence=0.9)
    rel = _rel(source.id, downstream.id, confidence=0.7)

    e_repo = AsyncMock()
    e_repo.get_by_id.side_effect = lambda eid: (
        source if eid == source.id else downstream
    )
    r_repo = AsyncMock()
    r_repo.get_outbound.side_effect = lambda eid, limit=500: (
        [rel] if eid == source.id else []
    )

    svc = _make_svc(e_repo, r_repo)
    await svc.propagate(source.id, max_hops=1)

    # path_conf = min(0.9, 0.7, 0.9) = 0.7 = rel.confidence → no cap needed
    r_repo.update_confidence.assert_not_called()


@pytest.mark.asyncio
async def test_propagate_3hops_reaches_grandchildren():
    """BFS propagates A→B→C→D within max_hops=3."""
    a = _entity("A", confidence=0.9)
    b = _entity("B", confidence=0.85)
    c = _entity("C", confidence=0.8)
    d = _entity("D", confidence=0.75)

    rel_ab = _rel(a.id, b.id, confidence=0.9)
    rel_bc = _rel(b.id, c.id, confidence=0.85)
    rel_cd = _rel(c.id, d.id, confidence=0.8)

    entity_map = {a.id: a, b.id: b, c.id: c, d.id: d}
    rel_map = {a.id: [rel_ab], b.id: [rel_bc], c.id: [rel_cd], d.id: []}

    e_repo = AsyncMock()
    e_repo.get_by_id.side_effect = lambda eid: entity_map.get(eid)
    r_repo = AsyncMock()
    r_repo.get_outbound.side_effect = lambda eid, limit=500: rel_map.get(eid, [])

    svc = _make_svc(e_repo, r_repo)
    result = await svc.propagate(a.id, max_hops=3)

    assert b.id in result.updated_entity_ids
    assert c.id in result.updated_entity_ids
    assert d.id in result.updated_entity_ids
    assert result.hops_reached == 3


@pytest.mark.asyncio
async def test_propagate_max_hops_1_does_not_reach_grandchild():
    a = _entity("A", confidence=0.9)
    b = _entity("B", confidence=0.8)
    c = _entity("C", confidence=0.7)
    rel_ab = _rel(a.id, b.id)
    rel_bc = _rel(b.id, c.id)

    entity_map = {a.id: a, b.id: b, c.id: c}
    rel_map = {a.id: [rel_ab], b.id: [rel_bc]}

    e_repo = AsyncMock()
    e_repo.get_by_id.side_effect = lambda eid: entity_map.get(eid)
    r_repo = AsyncMock()
    r_repo.get_outbound.side_effect = lambda eid, limit=500: rel_map.get(eid, [])

    svc = _make_svc(e_repo, r_repo)
    result = await svc.propagate(a.id, max_hops=1)

    assert b.id in result.updated_entity_ids
    assert c.id not in result.updated_entity_ids


@pytest.mark.asyncio
async def test_propagate_cycle_safe():
    """A→B→A must not loop infinitely."""
    a = _entity("A", confidence=0.9)
    b = _entity("B", confidence=0.8)
    rel_ab = _rel(a.id, b.id)
    rel_ba = _rel(b.id, a.id)

    entity_map = {a.id: a, b.id: b}
    rel_map = {a.id: [rel_ab], b.id: [rel_ba]}

    e_repo = AsyncMock()
    e_repo.get_by_id.side_effect = lambda eid: entity_map.get(eid)
    r_repo = AsyncMock()
    r_repo.get_outbound.side_effect = lambda eid, limit=500: rel_map.get(eid, [])

    svc = _make_svc(e_repo, r_repo)
    result = await svc.propagate(a.id, max_hops=5)

    # b should be updated exactly once (a is in visited from the start)
    assert result.updated_entity_ids.count(b.id) == 1


@pytest.mark.asyncio
async def test_recompute_for_entity_calls_trust_service():
    entity = _entity("E")
    e_repo = AsyncMock()
    e_repo.get_by_id.return_value = entity
    ts_svc = AsyncMock()

    svc = _make_svc(e_repo, AsyncMock(), ts_svc=ts_svc)
    await svc.recompute_for_entity(entity.id)

    ts_svc.compute_and_persist.assert_called_once()
    kwargs = ts_svc.compute_and_persist.call_args.kwargs
    assert kwargs["subject_id"] == entity.id
    assert kwargs["verification_state"] == entity.verification_state

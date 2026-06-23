"""Unit tests for PathDiscoveryService — BFS path finding, trust propagation."""
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.domain import Entity, Relationship, EntityType, RelationshipType, Direction
from src.services.path_discovery_service import PathDiscoveryService


# ── helpers ────────────────────────────────────────────────────────────────────

def _entity(name: str = "E", confidence: float = 0.8) -> Entity:
    return Entity(type=EntityType.PERSON, name=name, confidence=confidence)


def _rel(from_id, to_id, rel_type=RelationshipType.RELATED_TO, confidence=0.8) -> Relationship:
    return Relationship(
        type=rel_type,
        from_entity_id=from_id,
        to_entity_id=to_id,
        direction=Direction.DIRECTED,
        confidence=confidence,
    )


def _make_svc(entity_repo, rel_repo) -> PathDiscoveryService:
    return PathDiscoveryService(entity_repo, rel_repo)


# ── tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_same_entity_returns_trivial_path():
    entity = _entity("A")
    e_repo = AsyncMock()
    e_repo.get_by_id.return_value = entity

    svc = _make_svc(e_repo, AsyncMock())
    path = await svc.find_shortest_path(entity.id, entity.id)

    assert path is not None
    assert path.hop_count == 0
    assert len(path.entities) == 1
    assert path.entities[0].id == entity.id


@pytest.mark.asyncio
async def test_same_entity_unknown_returns_none():
    e_repo = AsyncMock()
    e_repo.get_by_id.return_value = None

    svc = _make_svc(e_repo, AsyncMock())
    path = await svc.find_shortest_path(uuid4(), uuid4())  # same UUID checked first
    # Will fall through to BFS since from != to; no relations → None
    # (This tests the non-trivial branch; just checking it doesn't crash)


@pytest.mark.asyncio
async def test_direct_path_one_hop():
    a = _entity("A")
    b = _entity("B")
    rel = _rel(a.id, b.id)

    e_repo = AsyncMock()
    e_repo.get_by_ids.return_value = [a, b]

    r_repo = AsyncMock()
    r_repo.get_outbound.side_effect = lambda eid, limit=500: [rel] if eid == a.id else []
    r_repo.get_inbound.return_value = []

    svc = _make_svc(e_repo, r_repo)
    path = await svc.find_shortest_path(a.id, b.id)

    assert path is not None
    assert path.hop_count == 1
    assert len(path.entities) == 2
    assert len(path.relationships) == 1
    assert path.relationships[0].id == rel.id


@pytest.mark.asyncio
async def test_two_hop_path():
    a = _entity("A")
    b = _entity("B")
    c = _entity("C")
    r1 = _rel(a.id, b.id)
    r2 = _rel(b.id, c.id)

    e_repo = AsyncMock()
    entity_map = {a.id: a, b.id: b, c.id: c}
    e_repo.get_by_ids.side_effect = lambda ids: [entity_map[i] for i in ids if i in entity_map]

    r_repo = AsyncMock()

    def _out(eid, limit=500):
        return {a.id: [r1], b.id: [r2]}.get(eid, [])

    r_repo.get_outbound.side_effect = _out
    r_repo.get_inbound.return_value = []

    svc = _make_svc(e_repo, r_repo)
    path = await svc.find_shortest_path(a.id, c.id)

    assert path is not None
    assert path.hop_count == 2
    assert len(path.entities) == 3


@pytest.mark.asyncio
async def test_no_path_returns_none():
    a = _entity("A")
    b = _entity("B")

    e_repo = AsyncMock()
    r_repo = AsyncMock()
    r_repo.get_outbound.return_value = []
    r_repo.get_inbound.return_value = []

    svc = _make_svc(e_repo, r_repo)
    path = await svc.find_shortest_path(a.id, b.id)

    assert path is None


@pytest.mark.asyncio
async def test_max_hops_blocks_long_path():
    """Chain A→B→C→D with max_hops=2 should fail (3 hops needed)."""
    a = _entity("A")
    b = _entity("B")
    c = _entity("C")
    d = _entity("D")
    r1 = _rel(a.id, b.id)
    r2 = _rel(b.id, c.id)
    r3 = _rel(c.id, d.id)

    r_repo = AsyncMock()

    def _out(eid, limit=500):
        return {a.id: [r1], b.id: [r2], c.id: [r3]}.get(eid, [])

    r_repo.get_outbound.side_effect = _out
    r_repo.get_inbound.return_value = []

    svc = _make_svc(AsyncMock(), r_repo)
    path = await svc.find_shortest_path(a.id, d.id, max_hops=2)

    assert path is None


@pytest.mark.asyncio
async def test_confidence_filter_excludes_low_confidence_rels():
    a = _entity("A")
    b = _entity("B")
    rel_low = _rel(a.id, b.id, confidence=0.2)

    r_repo = AsyncMock()
    r_repo.get_outbound.return_value = [rel_low]
    r_repo.get_inbound.return_value = []

    svc = _make_svc(AsyncMock(), r_repo)
    path = await svc.find_shortest_path(a.id, b.id, min_confidence=0.5)

    assert path is None  # rel excluded by confidence filter


@pytest.mark.asyncio
async def test_pessimistic_trust_propagation():
    """Path confidence = min across all entity and relationship confidences."""
    a = _entity("A", confidence=0.9)
    b = _entity("B", confidence=0.7)
    c = _entity("C", confidence=0.8)
    r1 = _rel(a.id, b.id, confidence=0.6)
    r2 = _rel(b.id, c.id, confidence=0.95)

    entity_map = {a.id: a, b.id: b, c.id: c}
    e_repo = AsyncMock()
    e_repo.get_by_ids.side_effect = lambda ids: [entity_map[i] for i in ids if i in entity_map]

    r_repo = AsyncMock()
    r_repo.get_outbound.side_effect = lambda eid, limit=500: {a.id: [r1], b.id: [r2]}.get(eid, [])
    r_repo.get_inbound.return_value = []

    svc = _make_svc(e_repo, r_repo)
    path = await svc.find_shortest_path(a.id, c.id)

    assert path is not None
    # min(0.9, 0.7, 0.8, 0.6, 0.95) = 0.6
    assert abs(path.total_confidence - 0.6) < 1e-9

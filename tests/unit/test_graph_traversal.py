"""Unit tests for GraphTraversalService — BFS correctness, cycle safety, filters."""
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.domain import Entity, Relationship, EntityType, RelationshipType, Direction
from src.services.graph_traversal_service import GraphTraversalService


# ── helpers ────────────────────────────────────────────────────────────────────

def _entity(name: str = "E", confidence: float = 0.8) -> Entity:
    return Entity(type=EntityType.PERSON, name=name, confidence=confidence)


def _rel(from_id, to_id, rel_type=RelationshipType.RELATED_TO, confidence: float = 0.8) -> Relationship:
    return Relationship(
        type=rel_type,
        from_entity_id=from_id,
        to_entity_id=to_id,
        direction=Direction.DIRECTED,
        confidence=confidence,
    )


def _make_svc(entity_repo, rel_repo) -> GraphTraversalService:
    return GraphTraversalService(entity_repo, rel_repo)


# ── tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_traverse_unknown_root_returns_empty():
    e_repo = AsyncMock()
    e_repo.get_by_id.return_value = None
    svc = _make_svc(e_repo, AsyncMock())
    result = await svc.traverse(uuid4())
    assert result.nodes == []
    assert result.edges == []
    assert result.truncated is False


@pytest.mark.asyncio
async def test_traverse_isolated_root_returns_only_root():
    root = _entity("Root")
    e_repo = AsyncMock()
    e_repo.get_by_id.return_value = root
    r_repo = AsyncMock()
    r_repo.get_outbound.return_value = []
    r_repo.get_inbound.return_value = []
    e_repo.get_by_ids.return_value = []

    svc = _make_svc(e_repo, r_repo)
    result = await svc.traverse(root.id)

    assert len(result.nodes) == 1
    assert result.nodes[0].id == root.id
    assert result.edges == []
    assert result.truncated is False


@pytest.mark.asyncio
async def test_traverse_depth1_outbound_returns_neighbor():
    root = _entity("Root")
    neighbor = _entity("Neighbor")
    rel = _rel(root.id, neighbor.id)

    e_repo = AsyncMock()
    e_repo.get_by_id.return_value = root
    e_repo.get_by_ids.return_value = [neighbor]

    r_repo = AsyncMock()
    r_repo.get_outbound.return_value = [rel]
    r_repo.get_inbound.return_value = []

    svc = _make_svc(e_repo, r_repo)
    result = await svc.traverse(root.id, max_depth=1, direction="OUTBOUND")

    assert len(result.nodes) == 2
    assert len(result.edges) == 1
    assert result.truncated is False


@pytest.mark.asyncio
async def test_traverse_depth2_returns_grandchild():
    root = _entity("Root")
    child = _entity("Child")
    grandchild = _entity("Grandchild")
    rel1 = _rel(root.id, child.id)
    rel2 = _rel(child.id, grandchild.id)

    e_repo = AsyncMock()
    # get_by_id only called for root; get_by_ids for each frontier level
    e_repo.get_by_id.return_value = root

    def _get_by_ids(ids):
        mapping = {child.id: child, grandchild.id: grandchild}
        return [mapping[i] for i in ids if i in mapping]
    e_repo.get_by_ids.side_effect = _get_by_ids

    def _outbound(entity_id, limit=100):
        if entity_id == root.id:
            return [rel1]
        if entity_id == child.id:
            return [rel2]
        return []
    r_repo = AsyncMock()
    r_repo.get_outbound.side_effect = _outbound
    r_repo.get_inbound.return_value = []

    svc = _make_svc(e_repo, r_repo)
    result = await svc.traverse(root.id, max_depth=2, direction="OUTBOUND")

    ids = {n.id for n in result.nodes}
    assert root.id in ids
    assert child.id in ids
    assert grandchild.id in ids
    assert len(result.edges) == 2


@pytest.mark.asyncio
async def test_traverse_circular_graph_no_infinite_loop():
    """A → B → A must not loop; BFS visited set breaks the cycle."""
    a = _entity("A")
    b = _entity("B")
    rel_ab = _rel(a.id, b.id)
    rel_ba = _rel(b.id, a.id)

    e_repo = AsyncMock()
    e_repo.get_by_id.return_value = a
    e_repo.get_by_ids.return_value = [b]

    def _outbound(entity_id, limit=100):
        if entity_id == a.id:
            return [rel_ab]
        if entity_id == b.id:
            return [rel_ba]
        return []
    r_repo = AsyncMock()
    r_repo.get_outbound.side_effect = _outbound
    r_repo.get_inbound.return_value = []

    svc = _make_svc(e_repo, r_repo)
    result = await svc.traverse(a.id, max_depth=5, direction="OUTBOUND")

    ids = {n.id for n in result.nodes}
    assert a.id in ids
    assert b.id in ids
    assert len(result.nodes) == 2  # no duplicates


@pytest.mark.asyncio
async def test_traverse_inbound_only_direction():
    root = _entity("Root")
    source = _entity("Source")
    rel = _rel(source.id, root.id)

    e_repo = AsyncMock()
    e_repo.get_by_id.return_value = root
    e_repo.get_by_ids.return_value = [source]

    r_repo = AsyncMock()
    r_repo.get_outbound.return_value = []
    r_repo.get_inbound.side_effect = lambda eid, limit=100: [rel] if eid == root.id else []

    svc = _make_svc(e_repo, r_repo)
    result = await svc.traverse(root.id, max_depth=1, direction="INBOUND")

    ids = {n.id for n in result.nodes}
    assert root.id in ids
    assert source.id in ids


@pytest.mark.asyncio
async def test_traverse_rel_type_filter_excludes_other_types():
    root = _entity("Root")
    a = _entity("A")
    b = _entity("B")
    rel_keep = _rel(root.id, a.id, RelationshipType.DEPENDS_ON)
    rel_skip = _rel(root.id, b.id, RelationshipType.RELATED_TO)

    e_repo = AsyncMock()
    e_repo.get_by_id.return_value = root
    e_repo.get_by_ids.side_effect = lambda ids: [a] if a.id in ids else []

    r_repo = AsyncMock()
    r_repo.get_outbound.return_value = [rel_keep, rel_skip]
    r_repo.get_inbound.return_value = []

    svc = _make_svc(e_repo, r_repo)
    result = await svc.traverse(
        root.id, max_depth=1, direction="OUTBOUND",
        rel_types=[RelationshipType.DEPENDS_ON],
    )

    ids = {n.id for n in result.nodes}
    assert a.id in ids
    assert b.id not in ids
    assert len(result.edges) == 1


@pytest.mark.asyncio
async def test_traverse_min_confidence_filter():
    root = _entity("Root")
    high = _entity("High")
    low = _entity("Low")
    rel_high = _rel(root.id, high.id, confidence=0.9)
    rel_low = _rel(root.id, low.id, confidence=0.3)

    e_repo = AsyncMock()
    e_repo.get_by_id.return_value = root
    e_repo.get_by_ids.side_effect = lambda ids: [high] if high.id in ids else []

    r_repo = AsyncMock()
    r_repo.get_outbound.return_value = [rel_high, rel_low]
    r_repo.get_inbound.return_value = []

    svc = _make_svc(e_repo, r_repo)
    result = await svc.traverse(root.id, max_depth=1, min_confidence=0.7)

    ids = {n.id for n in result.nodes}
    assert high.id in ids
    assert low.id not in ids


@pytest.mark.asyncio
async def test_traverse_limit_sets_truncated():
    root = _entity("Root")
    neighbors = [_entity(f"N{i}") for i in range(10)]
    rels = [_rel(root.id, n.id) for n in neighbors]

    e_repo = AsyncMock()
    e_repo.get_by_id.return_value = root
    # Return all 10 even though limit=3 (service enforces limit during node insertion)
    e_repo.get_by_ids.return_value = neighbors

    r_repo = AsyncMock()
    r_repo.get_outbound.return_value = rels
    r_repo.get_inbound.return_value = []

    svc = _make_svc(e_repo, r_repo)
    result = await svc.traverse(root.id, max_depth=1, limit=3)

    assert result.truncated is True
    assert len(result.nodes) <= 3


@pytest.mark.asyncio
async def test_get_neighbors_is_depth1_traversal():
    root = _entity("Root")
    child = _entity("Child")
    grandchild = _entity("Grandchild")
    rel1 = _rel(root.id, child.id)
    rel2 = _rel(child.id, grandchild.id)

    e_repo = AsyncMock()
    e_repo.get_by_id.return_value = root
    e_repo.get_by_ids.return_value = [child]

    def _outbound(entity_id, limit=100):
        return [rel1] if entity_id == root.id else [rel2]
    r_repo = AsyncMock()
    r_repo.get_outbound.side_effect = _outbound
    r_repo.get_inbound.return_value = []

    svc = _make_svc(e_repo, r_repo)
    result = await svc.get_neighbors(root.id, direction="OUTBOUND")

    ids = {n.id for n in result.nodes}
    assert child.id in ids
    assert grandchild.id not in ids  # depth=1 stops at immediate neighbors

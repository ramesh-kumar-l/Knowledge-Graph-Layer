"""Integration tests for Phase 5 Query Engine — SQLite in-memory fixture.

Graph fixture layout:
  Alice(PERSON) --ASSIGNED_TO--> Task1(TASK)
  Alice(PERSON) --MEMBER_OF-->   ProjectA(PROJECT)
  Bob(PERSON)   --ASSIGNED_TO--> Task2(TASK)
  Bob(PERSON)   --REPORTS_TO-->  Alice(PERSON)
  Task1         --WORKS_TOWARD-> Goal1(GOAL)
  Task2         --WORKS_TOWARD-> Goal1(GOAL)
  ProjectA      --CONTAINS-->    Task1
  Orphan(PERSON) — no edges

Shortest paths:
  Bob → Alice : 1 hop
  Bob → Task1 : 2 hops (Bob→Alice→Task1)
"""
import time
from uuid import uuid4

import pytest

from src.domain import (
    CreateEntityCommand, CreateRelationshipCommand,
    EntityType, RelationshipType,
)
from src.services.graph_traversal_service import GraphTraversalService
from src.services.path_discovery_service import PathDiscoveryService


# ── helpers ─────────────────────────────────────────────────────────────────────

async def _entity(adapter, entity_type: EntityType, name: str):
    return await adapter.create(CreateEntityCommand(type=entity_type, name=name))


async def _rel(r_adapter, from_id, to_id, rel_type: RelationshipType, confidence: float = 0.8):
    rel = await r_adapter.create(
        CreateRelationshipCommand(type=rel_type, from_entity_id=from_id, to_entity_id=to_id)
    )
    return await r_adapter.update_confidence(rel.id, confidence, "test")


def _traversal_svc(entity_adapter, relationship_adapter) -> GraphTraversalService:
    return GraphTraversalService(entity_adapter, relationship_adapter)


def _path_svc(entity_adapter, relationship_adapter) -> PathDiscoveryService:
    return PathDiscoveryService(entity_adapter, relationship_adapter)


@pytest.fixture
async def graph(entity_adapter, relationship_adapter):
    alice = await _entity(entity_adapter, EntityType.PERSON, "Alice")
    bob = await _entity(entity_adapter, EntityType.PERSON, "Bob")
    task1 = await _entity(entity_adapter, EntityType.TASK, "Task1")
    task2 = await _entity(entity_adapter, EntityType.TASK, "Task2")
    project_a = await _entity(entity_adapter, EntityType.PROJECT, "ProjectA")
    goal1 = await _entity(entity_adapter, EntityType.GOAL, "Goal1")
    orphan = await _entity(entity_adapter, EntityType.PERSON, "Orphan")

    await _rel(relationship_adapter, alice.id, task1.id, RelationshipType.ASSIGNED_TO)
    await _rel(relationship_adapter, alice.id, project_a.id, RelationshipType.MEMBER_OF)
    await _rel(relationship_adapter, bob.id, task2.id, RelationshipType.ASSIGNED_TO)
    await _rel(relationship_adapter, bob.id, alice.id, RelationshipType.REPORTS_TO)
    await _rel(relationship_adapter, task1.id, goal1.id, RelationshipType.WORKS_TOWARD)
    await _rel(relationship_adapter, task2.id, goal1.id, RelationshipType.WORKS_TOWARD)
    await _rel(relationship_adapter, project_a.id, task1.id, RelationshipType.CONTAINS)

    return dict(
        alice=alice, bob=bob, task1=task1, task2=task2,
        project_a=project_a, goal1=goal1, orphan=orphan,
    )


# ── graph traversal ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_graph_depth1_outbound(entity_adapter, relationship_adapter, graph):
    svc = _traversal_svc(entity_adapter, relationship_adapter)
    result = await svc.traverse(graph["alice"].id, max_depth=1, direction="OUTBOUND")
    ids = {n.id for n in result.nodes}
    assert graph["alice"].id in ids
    assert graph["task1"].id in ids
    assert graph["project_a"].id in ids
    assert graph["goal1"].id not in ids  # 2 hops away


@pytest.mark.asyncio
async def test_graph_depth2_reaches_grandchild(entity_adapter, relationship_adapter, graph):
    svc = _traversal_svc(entity_adapter, relationship_adapter)
    result = await svc.traverse(graph["alice"].id, max_depth=2, direction="OUTBOUND")
    ids = {n.id for n in result.nodes}
    assert graph["goal1"].id in ids  # Alice → Task1 → Goal1


@pytest.mark.asyncio
async def test_graph_inbound_direction(entity_adapter, relationship_adapter, graph):
    svc = _traversal_svc(entity_adapter, relationship_adapter)
    result = await svc.traverse(graph["goal1"].id, max_depth=1, direction="INBOUND")
    ids = {n.id for n in result.nodes}
    assert graph["task1"].id in ids
    assert graph["task2"].id in ids


@pytest.mark.asyncio
async def test_graph_both_directions(entity_adapter, relationship_adapter, graph):
    svc = _traversal_svc(entity_adapter, relationship_adapter)
    result = await svc.traverse(graph["task1"].id, max_depth=1, direction="BOTH")
    ids = {n.id for n in result.nodes}
    assert graph["goal1"].id in ids       # outbound
    assert graph["alice"].id in ids       # inbound
    assert graph["project_a"].id in ids   # inbound


@pytest.mark.asyncio
async def test_graph_neighbors_depth1_only(entity_adapter, relationship_adapter, graph):
    svc = _traversal_svc(entity_adapter, relationship_adapter)
    result = await svc.get_neighbors(graph["alice"].id, direction="OUTBOUND")
    ids = {n.id for n in result.nodes}
    assert graph["task1"].id in ids
    assert graph["goal1"].id not in ids  # 2 hops


@pytest.mark.asyncio
async def test_graph_unknown_entity_returns_empty(entity_adapter, relationship_adapter):
    svc = _traversal_svc(entity_adapter, relationship_adapter)
    result = await svc.traverse(uuid4())
    assert result.nodes == []
    assert result.edges == []
    assert result.truncated is False


@pytest.mark.asyncio
async def test_graph_circular_no_infinite_loop(entity_adapter, relationship_adapter):
    a = await _entity(entity_adapter, EntityType.CONCEPT, "CA")
    b = await _entity(entity_adapter, EntityType.CONCEPT, "CB")
    await relationship_adapter.create(CreateRelationshipCommand(
        type=RelationshipType.RELATED_TO, from_entity_id=a.id, to_entity_id=b.id
    ))
    await relationship_adapter.create(CreateRelationshipCommand(
        type=RelationshipType.RELATED_TO, from_entity_id=b.id, to_entity_id=a.id
    ))
    svc = _traversal_svc(entity_adapter, relationship_adapter)
    result = await svc.traverse(a.id, max_depth=5)
    ids = {n.id for n in result.nodes}
    assert a.id in ids
    assert b.id in ids
    assert len(result.nodes) == 2  # no phantom duplicates


@pytest.mark.asyncio
async def test_graph_rel_type_filter(entity_adapter, relationship_adapter, graph):
    svc = _traversal_svc(entity_adapter, relationship_adapter)
    result = await svc.traverse(
        graph["alice"].id, max_depth=1, direction="OUTBOUND",
        rel_types=[RelationshipType.ASSIGNED_TO],
    )
    ids = {n.id for n in result.nodes}
    assert graph["task1"].id in ids
    assert graph["project_a"].id not in ids  # MEMBER_OF excluded


# ── path discovery ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_path_direct_one_hop(entity_adapter, relationship_adapter, graph):
    svc = _path_svc(entity_adapter, relationship_adapter)
    path = await svc.find_shortest_path(graph["bob"].id, graph["alice"].id)
    assert path is not None
    assert path.hop_count == 1


@pytest.mark.asyncio
async def test_path_two_hops(entity_adapter, relationship_adapter, graph):
    svc = _path_svc(entity_adapter, relationship_adapter)
    path = await svc.find_shortest_path(graph["bob"].id, graph["task1"].id)
    assert path is not None
    assert path.hop_count == 2


@pytest.mark.asyncio
async def test_path_same_entity(entity_adapter, relationship_adapter, graph):
    svc = _path_svc(entity_adapter, relationship_adapter)
    path = await svc.find_shortest_path(graph["alice"].id, graph["alice"].id)
    assert path is not None
    assert path.hop_count == 0


@pytest.mark.asyncio
async def test_path_not_found_for_orphan(entity_adapter, relationship_adapter, graph):
    svc = _path_svc(entity_adapter, relationship_adapter)
    path = await svc.find_shortest_path(graph["alice"].id, graph["orphan"].id)
    assert path is None


# ── performance ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_depth3_traversal_under_200ms(entity_adapter, relationship_adapter):
    """Build a 31-node star+branch graph; depth-3 traversal must complete < 200ms."""
    hub = await _entity(entity_adapter, EntityType.CONCEPT, "Hub")

    for i in range(5):
        spoke = await _entity(entity_adapter, EntityType.CONCEPT, f"Spoke{i}")
        await relationship_adapter.create(CreateRelationshipCommand(
            type=RelationshipType.RELATED_TO, from_entity_id=hub.id, to_entity_id=spoke.id
        ))
        for k in range(5):
            child = await _entity(entity_adapter, EntityType.CONCEPT, f"Child{i}{k}")
            await relationship_adapter.create(CreateRelationshipCommand(
                type=RelationshipType.RELATED_TO,
                from_entity_id=spoke.id,
                to_entity_id=child.id,
            ))

    svc = _traversal_svc(entity_adapter, relationship_adapter)
    start = time.perf_counter()
    result = await svc.traverse(hub.id, max_depth=3, direction="OUTBOUND")
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms < 200, f"Traversal took {elapsed_ms:.1f}ms — exceeded 200ms p99 threshold"
    assert len(result.nodes) >= 31  # hub + 5 spokes + 25 children

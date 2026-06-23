"""BFS graph traversal service — depth-N, direction-aware, cycle-safe.

Pessimistic trust propagation per 14-trust-model.md: path confidence = min
of all hop confidences. Batch-fetches frontier entities per level for performance.
"""
from dataclasses import dataclass, field
from uuid import UUID

from src.domain import Entity, Relationship, RelationshipType
from src.repositories import EntityRepository, RelationshipRepository


@dataclass
class GraphResult:
    nodes: list[Entity]
    edges: list[Relationship]
    truncated: bool = False


class GraphTraversalService:
    """BFS traversal from a root entity up to max_depth hops."""

    def __init__(
        self,
        entity_repo: EntityRepository,
        rel_repo: RelationshipRepository,
    ) -> None:
        self._entities = entity_repo
        self._rels = rel_repo

    async def traverse(
        self,
        start_entity_id: UUID,
        max_depth: int = 3,
        direction: str = "BOTH",
        rel_types: list[RelationshipType] | None = None,
        min_confidence: float = 0.0,
        limit: int = 100,
    ) -> GraphResult:
        root = await self._entities.get_by_id(start_entity_id)
        if not root:
            return GraphResult(nodes=[], edges=[], truncated=False)

        nodes: dict[UUID, Entity] = {start_entity_id: root}
        edges: dict[UUID, Relationship] = {}
        frontier: set[UUID] = {start_entity_id}
        visited: set[UUID] = {start_entity_id}
        truncated = False

        for _ in range(max_depth):
            if not frontier:
                break

            next_frontier: set[UUID] = set()

            for entity_id in frontier:
                rels = await self._fetch_rels(
                    entity_id, direction, rel_types, min_confidence
                )
                for rel in rels:
                    if rel.id not in edges:
                        edges[rel.id] = rel
                    neighbor_id = (
                        rel.to_entity_id
                        if rel.from_entity_id == entity_id
                        else rel.from_entity_id
                    )
                    if neighbor_id not in visited:
                        visited.add(neighbor_id)
                        next_frontier.add(neighbor_id)

            # Batch-fetch new frontier entities (single DB round-trip per level)
            if next_frontier:
                fetched = await self._entities.get_by_ids(list(next_frontier))
                for entity in fetched:
                    if len(nodes) >= limit:
                        truncated = True
                        break
                    nodes[entity.id] = entity

            # Only continue BFS for nodes that were actually fetched
            frontier = {eid for eid in next_frontier if eid in nodes}

        return GraphResult(
            nodes=list(nodes.values()),
            edges=list(edges.values()),
            truncated=truncated,
        )

    async def get_neighbors(
        self,
        entity_id: UUID,
        direction: str = "BOTH",
        rel_types: list[RelationshipType] | None = None,
        min_confidence: float = 0.0,
        limit: int = 100,
    ) -> GraphResult:
        """Depth-1 traversal — direct neighbors only."""
        return await self.traverse(
            start_entity_id=entity_id,
            max_depth=1,
            direction=direction,
            rel_types=rel_types,
            min_confidence=min_confidence,
            limit=limit,
        )

    async def _fetch_rels(
        self,
        entity_id: UUID,
        direction: str,
        rel_types: list[RelationshipType] | None,
        min_confidence: float,
    ) -> list[Relationship]:
        rels: list[Relationship] = []
        if direction in ("OUTBOUND", "BOTH"):
            rels.extend(await self._rels.get_outbound(entity_id, limit=500))
        if direction in ("INBOUND", "BOTH"):
            rels.extend(await self._rels.get_inbound(entity_id, limit=500))

        return [
            r for r in rels
            if r.confidence >= min_confidence
            and (rel_types is None or r.type in rel_types)
        ]

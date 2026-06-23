"""BFS shortest-path discovery between two entities.

Trust propagation: pessimistic (14-trust-model.md) — path confidence =
min(confidence) across all entity and relationship nodes in the path.
"""
from collections import deque
from dataclasses import dataclass
from uuid import UUID

from src.domain import Entity, Relationship, RelationshipType
from src.repositories import EntityRepository, RelationshipRepository


@dataclass
class DiscoveredPath:
    entities: list[Entity]
    relationships: list[Relationship]
    hop_count: int
    total_confidence: float


class PathDiscoveryService:
    """BFS from source entity to find shortest path to target."""

    def __init__(
        self,
        entity_repo: EntityRepository,
        rel_repo: RelationshipRepository,
    ) -> None:
        self._entities = entity_repo
        self._rels = rel_repo

    async def find_shortest_path(
        self,
        from_entity_id: UUID,
        to_entity_id: UUID,
        max_hops: int = 4,
        min_confidence: float = 0.0,
        rel_types: list[RelationshipType] | None = None,
    ) -> DiscoveredPath | None:
        if from_entity_id == to_entity_id:
            entity = await self._entities.get_by_id(from_entity_id)
            if not entity:
                return None
            return DiscoveredPath(
                entities=[entity],
                relationships=[],
                hop_count=0,
                total_confidence=entity.confidence,
            )

        # BFS state: (current_id, ordered_entity_id_path, accumulated_rels)
        queue: deque[tuple[UUID, list[UUID], list[Relationship]]] = deque(
            [(from_entity_id, [from_entity_id], [])]
        )
        visited: set[UUID] = {from_entity_id}

        while queue:
            current_id, entity_path, rel_path = queue.popleft()
            if len(rel_path) >= max_hops:
                continue

            rels = await self._fetch_rels(current_id, min_confidence, rel_types)
            for rel in rels:
                neighbor_id = (
                    rel.to_entity_id
                    if rel.from_entity_id == current_id
                    else rel.from_entity_id
                )
                new_rel_path = rel_path + [rel]
                new_entity_path = entity_path + [neighbor_id]

                if neighbor_id == to_entity_id:
                    return await self._build_path(new_entity_path, new_rel_path)

                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, new_entity_path, new_rel_path))

        return None

    async def _build_path(
        self,
        entity_ids: list[UUID],
        rels: list[Relationship],
    ) -> DiscoveredPath:
        fetched = await self._entities.get_by_ids(entity_ids)
        entity_map = {e.id: e for e in fetched}
        ordered = [entity_map[eid] for eid in entity_ids if eid in entity_map]

        # Pessimistic trust propagation — weakest link determines path strength
        confidences = [e.confidence for e in ordered] + [r.confidence for r in rels]
        total_confidence = min(confidences) if confidences else 0.0

        return DiscoveredPath(
            entities=ordered,
            relationships=rels,
            hop_count=len(rels),
            total_confidence=total_confidence,
        )

    async def _fetch_rels(
        self,
        entity_id: UUID,
        min_confidence: float,
        rel_types: list[RelationshipType] | None,
    ) -> list[Relationship]:
        rels: list[Relationship] = []
        rels.extend(await self._rels.get_outbound(entity_id, limit=500))
        rels.extend(await self._rels.get_inbound(entity_id, limit=500))
        return [
            r for r in rels
            if r.confidence >= min_confidence
            and (rel_types is None or r.type in rel_types)
        ]

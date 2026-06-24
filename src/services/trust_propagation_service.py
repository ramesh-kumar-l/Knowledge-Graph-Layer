"""Trust propagation service — ripples score changes downstream via BFS.

When an entity's trust score or verification state changes, all entities
reachable outbound within max_hops have their relationship confidences
capped by pessimistic path confidence (min across all hops), then their
TrustScores are recomputed.  Per 14-trust-model.md.
"""
import logging
from dataclasses import dataclass, field
from uuid import UUID

from src.domain import SubjectType, VerificationState
from src.repositories import (
    EntityRepository, RelationshipRepository, TrustScoreRepository,
)
from src.services.trust_score_service import TrustScoreService

log = logging.getLogger(__name__)


@dataclass
class PropagationResult:
    source_entity_id: UUID
    updated_entity_ids: list[UUID] = field(default_factory=list)
    updated_rel_ids: list[UUID] = field(default_factory=list)
    hops_reached: int = 0


class TrustPropagationService:
    """Propagate trust changes outbound up to max_hops via pessimistic BFS."""

    def __init__(
        self,
        entity_repo: EntityRepository,
        rel_repo: RelationshipRepository,
        trust_repo: TrustScoreRepository,
        trust_score_svc: TrustScoreService,
    ) -> None:
        self._entities = entity_repo
        self._rels = rel_repo
        self._trust_repo = trust_repo
        self._trust_svc = trust_score_svc

    async def propagate(
        self,
        entity_id: UUID,
        max_hops: int = 3,
    ) -> PropagationResult:
        """Propagate confidence caps downstream from entity_id.

        For each downstream entity reached via BFS:
          - path_confidence = min(all entity + rel confidences on the path)
          - if a relationship's confidence exceeds path_confidence, cap it
          - recompute TrustScore for the downstream entity
        """
        result = PropagationResult(source_entity_id=entity_id)

        source = await self._entities.get_by_id(entity_id)
        if not source:
            log.warning("propagate: unknown source entity %s", entity_id)
            return result

        # BFS: queue holds (current_entity_id, path_confidence_so_far, hop_depth)
        queue: list[tuple[UUID, float, int]] = [(entity_id, source.confidence, 0)]
        visited: set[UUID] = {entity_id}

        while queue:
            current_id, path_conf, depth = queue.pop(0)
            if depth >= max_hops:
                continue

            rels = await self._rels.get_outbound(current_id, limit=500)
            for rel in rels:
                neighbor_id = rel.to_entity_id
                neighbor = await self._entities.get_by_id(neighbor_id)
                if not neighbor:
                    continue

                hop_path_conf = min(path_conf, rel.confidence, neighbor.confidence)

                # Cap relationship confidence if it exceeds the path confidence
                if rel.confidence > hop_path_conf:
                    await self._rels.update_confidence(rel.id, hop_path_conf, "trust-propagation")
                    result.updated_rel_ids.append(rel.id)
                    log.info(
                        "trust_propagation: rel=%s capped %.3f → %.3f",
                        rel.id, rel.confidence, hop_path_conf,
                    )

                # Recompute TrustScore for downstream entity
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    await self._trust_svc.compute_and_persist(
                        subject_type=SubjectType.ENTITY,
                        subject_id=neighbor_id,
                        verification_state=neighbor.verification_state,
                    )
                    result.updated_entity_ids.append(neighbor_id)
                    result.hops_reached = max(result.hops_reached, depth + 1)
                    queue.append((neighbor_id, hop_path_conf, depth + 1))

        log.info(
            "trust_propagation complete: source=%s updated_entities=%d updated_rels=%d",
            entity_id, len(result.updated_entity_ids), len(result.updated_rel_ids),
        )
        return result

    async def recompute_for_entity(self, entity_id: UUID) -> None:
        """Recompute TrustScore for a single entity without propagation."""
        entity = await self._entities.get_by_id(entity_id)
        if entity:
            await self._trust_svc.compute_and_persist(
                subject_type=SubjectType.ENTITY,
                subject_id=entity_id,
                verification_state=entity.verification_state,
            )

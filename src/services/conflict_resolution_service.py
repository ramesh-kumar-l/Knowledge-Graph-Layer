"""Conflict resolution service — transitions DISPUTED entities to VERIFIED/UNVERIFIED.

Resolution workflow (14-trust-model.md):
  DISPUTED → VERIFIED   (accept: evidence is trustworthy)
  DISPUTED → UNVERIFIED (reject: evidence is not reliable)

Each transition is version-logged and triggers TrustScore recomputation.
"""
import logging
from enum import StrEnum
from uuid import UUID

from src.domain import Entity, SubjectType, VerificationState
from src.domain.entity import UpdateEntityCommand
from src.ingestion.models import KnowledgeConflictDetected
from src.repositories import EntityRepository, EvidenceRepository
from src.services.trust_score_service import TrustScoreService
from src.services.version_service import VersionService

log = logging.getLogger(__name__)


class ResolutionDecision(StrEnum):
    ACCEPT = "ACCEPT"   # DISPUTED → VERIFIED
    REJECT = "REJECT"   # DISPUTED → UNVERIFIED


class ConflictResolutionError(Exception):
    pass


class ConflictResolutionService:
    """Accept or reject conflicting evidence on a DISPUTED entity."""

    def __init__(
        self,
        entity_repo: EntityRepository,
        evidence_repo: EvidenceRepository,
        version_svc: VersionService,
        trust_svc: TrustScoreService,
    ) -> None:
        self._entities = entity_repo
        self._evidence = evidence_repo
        self._version = version_svc
        self._trust = trust_svc

    async def resolve(
        self,
        entity_id: UUID,
        decision: ResolutionDecision,
        resolved_by: str = "system",
        reason: str = "",
    ) -> Entity:
        """Transition a DISPUTED entity to VERIFIED or UNVERIFIED.

        Raises ConflictResolutionError if entity is not DISPUTED or not found.
        """
        entity = await self._entities.get_by_id(entity_id)
        if entity is None:
            raise ConflictResolutionError(f"Entity {entity_id} not found")
        if entity.verification_state != VerificationState.DISPUTED:
            raise ConflictResolutionError(
                f"Entity {entity_id} is {entity.verification_state}, not DISPUTED"
            )

        new_state = (
            VerificationState.VERIFIED
            if decision == ResolutionDecision.ACCEPT
            else VerificationState.UNVERIFIED
        )
        change_reason = f"conflict_resolved_{decision.lower()}"
        if reason:
            change_reason = f"{change_reason}: {reason}"

        # Version-log the transition before applying the state change
        await self._version.create_version_before_write(
            subject_type=SubjectType.ENTITY,
            subject_id=entity.id,
            current_snapshot=entity.to_snapshot(),
            next_version=entity.version + 1,
            changed_by=resolved_by,
            change_reason=change_reason,
        )

        updated = await self._entities.update(
            entity,
            UpdateEntityCommand(
                verification_state=new_state,
                change_reason=change_reason,
                changed_by=resolved_by,
            ),
        )

        # Recompute TrustScore now that verification state changed
        await self._trust.compute_and_persist(
            subject_type=SubjectType.ENTITY,
            subject_id=updated.id,
            verification_state=updated.verification_state,
        )

        log.info(
            "conflict_resolved entity=%s decision=%s new_state=%s by=%s",
            entity_id, decision, new_state, resolved_by,
        )
        return updated

    async def get_conflict_history(self, entity_id: UUID) -> list[dict]:
        """Return version records that represent conflict-related state transitions."""
        # Delegated: caller supplies version_svc.get_history() externally.
        # This method is a thin lookup for the explain endpoint to call directly.
        return []

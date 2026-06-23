import logging

from src.domain import Entity, SubjectType, VerificationState
from src.domain.entity import UpdateEntityCommand
from src.repositories import EntityRepository, EvidenceRepository
from src.services import VersionService
from src.ingestion.models import KnowledgeConflictDetected

log = logging.getLogger(__name__)

# Attribute keys whose values are compared across evidence for conflicts.
_CONFLICTABLE_ATTRS = frozenset({
    "status", "role", "email", "level", "domain",
    "assignee_id", "priority", "due_date", "org_type",
})


class ConflictDetector:
    """Detect attribute contradictions across Evidence; flag entities DISPUTED.

    When two memory records assert different values for the same key,
    both records are retained and the entity is marked DISPUTED
    (11-memory-model.md — conflict detection rules).
    """

    def __init__(
        self,
        evidence_repo: EvidenceRepository,
        entity_repo: EntityRepository,
        version_svc: VersionService,
    ) -> None:
        self._evidence = evidence_repo
        self._entity = entity_repo
        self._version = version_svc

    async def detect_and_flag(
        self,
        entity: Entity,
        new_attributes: dict,
    ) -> list[KnowledgeConflictDetected]:
        """Compare new_attributes against prior evidence metadata for this entity.

        Side-effect: if a conflict is found, updates entity to DISPUTED and
        writes a version record.
        """
        if not new_attributes:
            return []

        evidence_list = await self._evidence.get_for_subject(
            SubjectType.ENTITY, entity.id
        )
        if not evidence_list:
            return []

        conflicts: list[KnowledgeConflictDetected] = []
        for attr_key, new_val in new_attributes.items():
            if attr_key not in _CONFLICTABLE_ATTRS:
                continue
            norm_new = str(new_val).strip().lower()
            conflicting_ids = []
            for ev in evidence_list:
                old_val = ev.metadata.get(attr_key)
                if old_val is None:
                    continue
                norm_old = str(old_val).strip().lower()
                if norm_old and norm_old != norm_new:
                    conflicting_ids.append(ev.id)
            if conflicting_ids:
                log.info(
                    "conflict entity=%s attr=%s values=%s vs %s",
                    entity.id, attr_key, norm_new,
                    [ev.metadata.get(attr_key) for ev in evidence_list
                     if ev.id in conflicting_ids],
                )
                conflicts.append(KnowledgeConflictDetected(
                    entity_id=entity.id,
                    attribute=attr_key,
                    evidence_ids=conflicting_ids,
                ))

        if conflicts and entity.verification_state != VerificationState.DISPUTED:
            await self._flag_disputed(entity)

        return conflicts

    async def _flag_disputed(self, entity: Entity) -> None:
        await self._version.create_version_before_write(
            subject_type=SubjectType.ENTITY,
            subject_id=entity.id,
            current_snapshot=entity.to_snapshot(),
            next_version=entity.version + 1,
            changed_by="conflict-detector",
            change_reason="conflict_detected",
        )
        await self._entity.update(
            entity,
            UpdateEntityCommand(
                verification_state=VerificationState.DISPUTED,
                change_reason="conflict_detected",
                changed_by="conflict-detector",
            ),
        )
        log.info("entity flagged DISPUTED: %s", entity.id)

"""Relationship Ingestion Pipeline — persists validated candidate relationships with evidence.

Steps per candidate:
  1. In-batch deduplication by (from_id, to_id, rel_type) key
  2. Entity-type constraint validation via RelationshipValidator
  3. DB-level idempotency check via RelationshipRepository.exists_by_entities
  4. Create Relationship record
  5. Attach Evidence + Provenance
  6. Compute TrustScore
  7. Emit RelationshipCreatedEvent
"""
import logging

from src.domain import SubjectType, EvidenceSourceType, VerificationState
from src.domain.relationship import CreateRelationshipCommand
from src.domain.evidence import CreateEvidenceCommand, CONTENT_MAX_CHARS
from src.domain.provenance import CreateProvenanceCommand
from src.repositories import RelationshipRepository, EvidenceRepository, ProvenanceRepository
from src.services import TrustScoreService
from src.adapters.postgres.evidence_adapter import DuplicateEvidenceError
from src.adapters.postgres.provenance_adapter import DuplicateProvenanceError
from src.ingestion.models import (
    MemoryRecord, CandidateRelationship, RelationshipCreatedEvent,
)
from src.ingestion.relationship_validator import RelationshipValidator

log = logging.getLogger(__name__)


class RelationshipIngestionPipeline:
    """Validates and persists extracted relationships. Stateless per call; thread-safe."""

    def __init__(
        self,
        rel_repo: RelationshipRepository,
        evidence_repo: EvidenceRepository,
        provenance_repo: ProvenanceRepository,
        trust_svc: TrustScoreService,
        validator: RelationshipValidator | None = None,
    ) -> None:
        self._rel = rel_repo
        self._evidence = evidence_repo
        self._provenance = provenance_repo
        self._trust = trust_svc
        self._validator = validator or RelationshipValidator()

    async def ingest(
        self,
        candidates: list[CandidateRelationship],
        record: MemoryRecord,
    ) -> tuple[int, int, list[dict]]:
        """Ingest candidate relationships for one MemoryRecord.

        Returns (relationships_created, relationships_skipped, events).
        """
        created = 0
        skipped = 0
        events: list[dict] = []
        seen: set[tuple] = set()

        for candidate in candidates:
            key = (
                candidate.from_entity_id,
                candidate.to_entity_id,
                candidate.relationship_type,
            )

            # In-batch deduplication
            if key in seen:
                skipped += 1
                continue
            seen.add(key)

            # Validate entity-type constraints
            valid, violation = self._validator.validate(candidate)
            if not valid:
                log.debug(
                    "relationship_pipeline.constraint_violated "
                    "type=%s from_type=%s to_type=%s",
                    candidate.relationship_type.value,
                    candidate.from_entity_type.value,
                    candidate.to_entity_type.value,
                )
                if violation:
                    events.append(violation.model_dump(mode="json"))
                skipped += 1
                continue

            # DB-level idempotency
            if await self._rel.exists_by_entities(
                candidate.from_entity_id,
                candidate.to_entity_id,
                candidate.relationship_type,
            ):
                log.debug("relationship_pipeline.skip duplicate key=%s", key)
                skipped += 1
                continue

            # Create relationship
            relationship = await self._rel.create(CreateRelationshipCommand(
                type=candidate.relationship_type,
                from_entity_id=candidate.from_entity_id,
                to_entity_id=candidate.to_entity_id,
            ))

            # Attach Evidence
            try:
                await self._evidence.create(CreateEvidenceCommand(
                    subject_type=SubjectType.RELATIONSHIP,
                    subject_id=relationship.id,
                    source_type=EvidenceSourceType.MEMORY,
                    source_id=record.id,
                    content=record.content[:CONTENT_MAX_CHARS],
                    confidence=candidate.confidence,
                    extractor_id="memory-ingestion-v1",
                    metadata={"extraction_reason": candidate.extraction_reason},
                ))
            except DuplicateEvidenceError:
                log.debug(
                    "relationship_pipeline.evidence_dup rel=%s source=%s",
                    relationship.id, record.id,
                )

            # Attach Provenance (one per relationship)
            try:
                await self._provenance.create(CreateProvenanceCommand(
                    subject_type=SubjectType.RELATIONSHIP,
                    subject_id=relationship.id,
                    origin="scp-memory-core",
                    extraction_method="memory_extraction",
                    raw_source_ref=record.id,
                    session_id=record.session_id,
                    agent_id=record.agent_id,
                ))
            except DuplicateProvenanceError:
                pass

            # Recompute TrustScore
            await self._trust.compute_and_persist(
                SubjectType.RELATIONSHIP, relationship.id, VerificationState.UNVERIFIED
            )

            events.append(RelationshipCreatedEvent(
                relationship_id=relationship.id,
                from_entity_id=candidate.from_entity_id,
                to_entity_id=candidate.to_entity_id,
                relationship_type=candidate.relationship_type.value,
                memory_record_id=record.id,
            ).model_dump(mode="json"))
            created += 1

        log.info(
            "relationship_pipeline.complete record=%s created=%d skipped=%d",
            record.id, created, skipped,
        )
        return created, skipped, events

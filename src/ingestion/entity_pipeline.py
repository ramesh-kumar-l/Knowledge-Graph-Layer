"""Entity Ingestion Pipeline — 9-step pipeline from MemoryRecord to KG entities.

Step sequence (11-memory-model.md):
  1. RECEIVE      Accept MemoryRecord
  2. DEDUPLICATE  Global idempotency check — skip if already ingested
  3. CLASSIFY     Extract candidate entities
  4. RESOLVE      Match candidates to existing entities
  5. EXTRACT      (Phase 4 — relationship extraction, skipped here)
  6. ATTACH       Create Evidence + Provenance
  7. SCORE        Compute TrustScore
  8. VERSION      Version record for new/changed entities
  9. EMIT         Return KnowledgeUpdatedEvent list
"""
import logging

from src.domain import SubjectType, EvidenceSourceType
from src.domain.entity import CreateEntityCommand
from src.domain.evidence import CreateEvidenceCommand, CONTENT_MAX_CHARS
from src.domain.provenance import CreateProvenanceCommand
from src.repositories import EntityRepository, EvidenceRepository, ProvenanceRepository
from src.services import TrustScoreService, VersionService
from src.adapters.postgres.evidence_adapter import DuplicateEvidenceError
from src.adapters.postgres.provenance_adapter import DuplicateProvenanceError
from src.ingestion.models import (
    MemoryRecord, IngestionResult, ResolutionStrategy,
    KnowledgeUpdatedEvent,
)
from src.ingestion.entity_extractor import EntityExtractor
from src.ingestion.deduplicator import DeduplicationEngine
from src.ingestion.conflict_detector import ConflictDetector

log = logging.getLogger(__name__)


class EntityIngestionPipeline:
    """Orchestrates the 9-step entity ingestion process. Thread-safe; stateless per call."""

    def __init__(
        self,
        entity_repo: EntityRepository,
        evidence_repo: EvidenceRepository,
        provenance_repo: ProvenanceRepository,
        trust_svc: TrustScoreService,
        version_svc: VersionService,
        extractor: EntityExtractor | None = None,
        deduplicator: DeduplicationEngine | None = None,
        conflict_detector: ConflictDetector | None = None,
    ) -> None:
        self._entity = entity_repo
        self._evidence = evidence_repo
        self._provenance = provenance_repo
        self._trust = trust_svc
        self._version = version_svc
        self._extractor = extractor or EntityExtractor()
        self._dedup = deduplicator or DeduplicationEngine(entity_repo)
        self._conflict = conflict_detector or ConflictDetector(
            evidence_repo, entity_repo, version_svc
        )

    async def ingest(self, record: MemoryRecord) -> IngestionResult:
        """Run full pipeline for one MemoryRecord. Idempotent — safe to re-submit."""
        # Steps 1+2: RECEIVE + global DEDUPLICATE check
        if await self._evidence.exists_by_source_id(record.id):
            log.info("pipeline.skip already_ingested record=%s", record.id)
            return IngestionResult(
                memory_record_id=record.id,
                status="SKIPPED_DUPLICATE",
            )

        # Step 3: CLASSIFY — extract candidates from record
        candidates = self._extractor.extract(record)
        if not candidates:
            log.info("pipeline.no_candidates record=%s", record.id)
            return IngestionResult(memory_record_id=record.id, status="PROCESSED")

        events: list[dict] = []
        entities_created = 0
        entities_matched = 0

        for candidate in candidates:
            # Step 4: RESOLVE — identity resolution
            resolution, dup_events = await self._dedup.resolve(candidate, record.id)
            for ev in dup_events:
                events.append(ev.model_dump(mode="json"))

            if resolution.strategy == ResolutionStrategy.NEW:
                entity = await self._entity.create(CreateEntityCommand(
                    type=candidate.entity_type,
                    name=candidate.name,
                    aliases=candidate.aliases,
                    attributes=candidate.attributes,
                    source_memory_ids=[record.id],
                    created_by="memory-ingestion-v1",
                ))
                entities_created += 1
                is_new = True
            else:
                entity = await self._entity.get_by_id(resolution.entity_id)
                if entity is None:
                    log.warning("resolved entity %s not found, skipping", resolution.entity_id)
                    continue
                entities_matched += 1
                is_new = False

            evidence_confidence = (
                resolution.confidence if resolution.confidence > 0.0
                else candidate.confidence
            )

            # Step 6a: ATTACH evidence
            try:
                await self._evidence.create(CreateEvidenceCommand(
                    subject_type=SubjectType.ENTITY,
                    subject_id=entity.id,
                    source_type=EvidenceSourceType.MEMORY,
                    source_id=record.id,
                    content=record.content[:CONTENT_MAX_CHARS],
                    confidence=evidence_confidence,
                    extractor_id="memory-ingestion-v1",
                    metadata={
                        "session_id": str(record.session_id),
                        "agent_id": record.agent_id,
                        **candidate.attributes,
                    },
                ))
            except DuplicateEvidenceError:
                log.debug("evidence already exists entity=%s source=%s", entity.id, record.id)

            # Step 6b: ATTACH provenance (new entities only — one per entity)
            if is_new:
                try:
                    await self._provenance.create(CreateProvenanceCommand(
                        subject_type=SubjectType.ENTITY,
                        subject_id=entity.id,
                        origin="scp-memory-core",
                        extraction_method="memory_extraction",
                        raw_source_ref=record.id,
                        session_id=record.session_id,
                        agent_id=record.agent_id,
                    ))
                except DuplicateProvenanceError:
                    pass

            # Step 7: SCORE — recompute trust after new evidence
            await self._trust.compute_and_persist(
                SubjectType.ENTITY, entity.id, entity.verification_state
            )

            # Conflict detection (inline with step 6)
            if candidate.attributes:
                conflict_events = await self._conflict.detect_and_flag(
                    entity, candidate.attributes
                )
                for ce in conflict_events:
                    events.append(ce.model_dump(mode="json"))

            # Step 9: EMIT
            events.append(KnowledgeUpdatedEvent(
                entity_id=entity.id,
                memory_record_id=record.id,
            ).model_dump(mode="json"))

        log.info(
            "pipeline.complete record=%s created=%d matched=%d events=%d",
            record.id, entities_created, entities_matched, len(events),
        )
        return IngestionResult(
            memory_record_id=record.id,
            status="PROCESSED",
            entities_created=entities_created,
            entities_matched=entities_matched,
            events=events,
        )

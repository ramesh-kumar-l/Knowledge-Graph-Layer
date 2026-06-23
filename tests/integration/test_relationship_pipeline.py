"""Integration tests for the full Relationship Engine (extractor + validator + pipeline).

Uses SQLite in-memory — same setup as entity pipeline tests.
"""
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.domain.entity import CreateEntityCommand
from src.domain.enums import EntityType, RelationshipType, SubjectType
from src.ingestion.models import (
    MemoryRecord, CandidateRelationship, ResolvedEntityRef,
)
from src.ingestion.relationship_extractor import RelationshipExtractor
from src.ingestion.relationship_pipeline import RelationshipIngestionPipeline
from src.ingestion.relationship_validator import RelationshipValidator
from src.services.trust_score_service import TrustScoreService


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def trust_service(evidence_adapter, trust_score_adapter):
    return TrustScoreService(evidence_adapter, trust_score_adapter)


@pytest.fixture
def rel_pipeline(relationship_adapter, evidence_adapter, provenance_adapter, trust_service):
    return RelationshipIngestionPipeline(
        rel_repo=relationship_adapter,
        evidence_repo=evidence_adapter,
        provenance_repo=provenance_adapter,
        trust_svc=trust_service,
        validator=RelationshipValidator(),
    )


@pytest.fixture
def extractor():
    return RelationshipExtractor()


def _record(content: str, metadata: dict | None = None) -> MemoryRecord:
    return MemoryRecord(
        id=str(uuid4()),
        content=content,
        timestamp=datetime.now(timezone.utc),
        metadata=metadata or {},
    )


def _candidate(
    from_ref: ResolvedEntityRef,
    to_ref: ResolvedEntityRef,
    rel_type: RelationshipType,
    confidence: float = 0.80,
) -> CandidateRelationship:
    return CandidateRelationship(
        from_entity_id=from_ref.entity_id,
        from_entity_type=from_ref.entity_type,
        to_entity_id=to_ref.entity_id,
        to_entity_type=to_ref.entity_type,
        relationship_type=rel_type,
        confidence=confidence,
    )


def _ref(name: str, entity_type: EntityType) -> ResolvedEntityRef:
    return ResolvedEntityRef(entity_id=uuid4(), entity_type=entity_type, name=name)


# ── relationship pipeline unit tests ─────────────────────────────────────────

class TestRelationshipPipelineIngest:
    @pytest.mark.asyncio
    async def test_creates_relationship(self, rel_pipeline, relationship_adapter):
        task_ref = _ref("Fix Bug", EntityType.TASK)
        person_ref = _ref("Alice Chen", EntityType.PERSON)
        record = _record("Fix Bug assigned to Alice Chen")
        candidates = [_candidate(task_ref, person_ref, RelationshipType.ASSIGNED_TO)]

        created, skipped, events = await rel_pipeline.ingest(candidates, record)

        assert created == 1
        assert skipped == 0
        rels = await relationship_adapter.list_active()
        assert len(rels) == 1
        assert rels[0].type == RelationshipType.ASSIGNED_TO

    @pytest.mark.asyncio
    async def test_idempotent_double_ingest(self, rel_pipeline, relationship_adapter):
        task_ref = _ref("Fix Bug", EntityType.TASK)
        person_ref = _ref("Alice Chen", EntityType.PERSON)
        record = _record("Fix Bug assigned to Alice Chen")
        candidates = [_candidate(task_ref, person_ref, RelationshipType.ASSIGNED_TO)]

        await rel_pipeline.ingest(candidates, record)
        created2, skipped2, _ = await rel_pipeline.ingest(candidates, _record("same content"))

        assert created2 == 0
        assert skipped2 == 1
        rels = await relationship_adapter.list_active()
        assert len(rels) == 1

    @pytest.mark.asyncio
    async def test_constraint_violation_skips_and_emits_event(self, rel_pipeline):
        person_ref = _ref("Alice Chen", EntityType.PERSON)
        project_ref = _ref("Backend Project", EntityType.PROJECT)
        record = _record("content")
        # ASSIGNED_TO from PERSON is invalid (must be from TASK)
        candidates = [_candidate(person_ref, project_ref, RelationshipType.ASSIGNED_TO)]

        created, skipped, events = await rel_pipeline.ingest(candidates, record)

        assert created == 0
        assert skipped == 1
        assert any(e["event_type"] == "RelationshipConstraintViolated" for e in events)

    @pytest.mark.asyncio
    async def test_in_batch_deduplication(self, rel_pipeline, relationship_adapter):
        task_ref = _ref("Fix Bug", EntityType.TASK)
        person_ref = _ref("Alice Chen", EntityType.PERSON)
        record = _record("Fix Bug assigned to Alice Chen twice.")
        candidates = [
            _candidate(task_ref, person_ref, RelationshipType.ASSIGNED_TO),
            _candidate(task_ref, person_ref, RelationshipType.ASSIGNED_TO),
        ]

        created, skipped, events = await rel_pipeline.ingest(candidates, record)

        assert created == 1
        assert skipped == 1
        rels = await relationship_adapter.list_active()
        assert len(rels) == 1

    @pytest.mark.asyncio
    async def test_relationship_created_event_emitted(self, rel_pipeline):
        task_ref = _ref("Fix Bug", EntityType.TASK)
        person_ref = _ref("Alice Chen", EntityType.PERSON)
        record = _record("Fix Bug assigned to Alice Chen")
        candidates = [_candidate(task_ref, person_ref, RelationshipType.ASSIGNED_TO)]

        created, _, events = await rel_pipeline.ingest(candidates, record)

        assert created == 1
        rel_events = [e for e in events if e["event_type"] == "RelationshipCreatedEvent"]
        assert len(rel_events) == 1
        assert rel_events[0]["relationship_type"] == RelationshipType.ASSIGNED_TO.value

    @pytest.mark.asyncio
    async def test_evidence_created_for_relationship(
        self, rel_pipeline, relationship_adapter, evidence_adapter
    ):
        task_ref = _ref("Deploy Service", EntityType.TASK)
        person_ref = _ref("Bob Smith", EntityType.PERSON)
        record = _record("Deploy Service assigned to Bob Smith")
        candidates = [_candidate(task_ref, person_ref, RelationshipType.ASSIGNED_TO)]

        await rel_pipeline.ingest(candidates, record)

        rels = await relationship_adapter.list_active()
        assert len(rels) == 1
        evidence = await evidence_adapter.get_for_subject(
            subject_type=SubjectType.RELATIONSHIP,
            subject_id=rels[0].id,
        )
        assert len(evidence) == 1
        assert evidence[0].source_id == record.id

    @pytest.mark.asyncio
    async def test_multiple_valid_candidates(self, rel_pipeline, relationship_adapter):
        task_ref = _ref("Fix Bug", EntityType.TASK)
        person_ref = _ref("Alice Chen", EntityType.PERSON)
        project_ref = _ref("Alpha Project", EntityType.PROJECT)
        goal_ref = _ref("Q3 Goal", EntityType.GOAL)
        record = _record("Fix Bug assigned to Alice Chen. Alpha Project works toward Q3 Goal.")
        candidates = [
            _candidate(task_ref, person_ref, RelationshipType.ASSIGNED_TO),
            _candidate(project_ref, goal_ref, RelationshipType.WORKS_TOWARD),
        ]

        created, skipped, events = await rel_pipeline.ingest(candidates, record)

        assert created == 2
        assert skipped == 0
        rels = await relationship_adapter.list_active()
        assert len(rels) == 2

    @pytest.mark.asyncio
    async def test_empty_candidates_returns_zero(self, rel_pipeline):
        record = _record("No entity content here")
        created, skipped, events = await rel_pipeline.ingest([], record)
        assert created == 0
        assert skipped == 0
        assert events == []


# ── extractor + pipeline end-to-end ──────────────────────────────────────────

class TestEndToEndRelationshipExtraction:
    @pytest.mark.asyncio
    async def test_extract_then_ingest(self, extractor, rel_pipeline, relationship_adapter):
        task_ref = _ref("Fix Login Bug", EntityType.TASK)
        person_ref = _ref("Alice Chen", EntityType.PERSON)
        record = _record("Fix Login Bug assigned to Alice Chen")

        candidates = extractor.extract(record, [task_ref, person_ref])
        created, _, _ = await rel_pipeline.ingest(candidates, record)

        assert created >= 1
        rels = await relationship_adapter.list_active()
        assert any(r.type == RelationshipType.ASSIGNED_TO for r in rels)

    @pytest.mark.asyncio
    async def test_metadata_driven_relationship(
        self, extractor, rel_pipeline, relationship_adapter
    ):
        task_ref = _ref("Deploy Service", EntityType.TASK)
        person_ref = _ref("Bob Smith", EntityType.PERSON)
        metadata = {
            "relationships": [
                {"from": "Deploy Service", "to": "Bob Smith", "type": "ASSIGNED_TO"}
            ]
        }
        record = _record("Some memory content.", metadata=metadata)

        candidates = extractor.extract(record, [task_ref, person_ref])
        created, _, _ = await rel_pipeline.ingest(candidates, record)

        assert created == 1
        rels = await relationship_adapter.list_active()
        assert rels[0].type == RelationshipType.ASSIGNED_TO

    @pytest.mark.asyncio
    async def test_constraint_violation_not_persisted(
        self, extractor, rel_pipeline, relationship_adapter
    ):
        person_ref = _ref("Alice Chen", EntityType.PERSON)
        org_ref = _ref("Eng Team", EntityType.ORGANIZATION)
        # "reports to" is PERSON→PERSON; PERSON→ORGANIZATION is invalid
        record = _record("Alice Chen reports to Eng Team")

        candidates = extractor.extract(record, [person_ref, org_ref])
        # All extracted relationships with wrong constraint will be blocked
        filtered_candidates = [
            c for c in candidates
            if c.relationship_type == RelationshipType.REPORTS_TO
        ]
        if filtered_candidates:
            created, skipped, events = await rel_pipeline.ingest(filtered_candidates, record)
            rels = await relationship_adapter.list_active()
            assert len(rels) == 0  # Constraint violation → nothing persisted

    @pytest.mark.asyncio
    async def test_double_extraction_idempotent(
        self, extractor, rel_pipeline, relationship_adapter
    ):
        task_ref = _ref("Fix Bug", EntityType.TASK)
        person_ref = _ref("Alice Chen", EntityType.PERSON)
        record = _record("Fix Bug assigned to Alice Chen")

        candidates = extractor.extract(record, [task_ref, person_ref])
        await rel_pipeline.ingest(candidates, record)
        # Second ingest with same entity pair
        candidates2 = extractor.extract(record, [task_ref, person_ref])
        created2, skipped2, _ = await rel_pipeline.ingest(candidates2, _record("Fix Bug assigned to Alice Chen"))

        rels = await relationship_adapter.list_active()
        assert len(rels) == 1  # Still only one relationship

    @pytest.mark.asyncio
    async def test_exists_by_entities_used_for_dedup(self, relationship_adapter, rel_pipeline):
        task_ref = _ref("Task A", EntityType.TASK)
        person_ref = _ref("Alice Chen", EntityType.PERSON)
        record = _record("Task A assigned to Alice Chen")

        # First ingest
        await rel_pipeline.ingest(
            [_candidate(task_ref, person_ref, RelationshipType.ASSIGNED_TO)], record
        )
        exists = await relationship_adapter.exists_by_entities(
            task_ref.entity_id,
            person_ref.entity_id,
            RelationshipType.ASSIGNED_TO,
        )
        assert exists is True

    @pytest.mark.asyncio
    async def test_exists_by_entities_false_for_nonexistent(self, relationship_adapter):
        exists = await relationship_adapter.exists_by_entities(
            uuid4(), uuid4(), RelationshipType.ASSIGNED_TO
        )
        assert exists is False
